#!/usr/bin/env python3
from ansible_playbook_runner import Runner
from jinja2 import Environment, FileSystemLoader
from io import StringIO
from flask import Flask, render_template, request, session, send_file
import re,json
import sys
import webbrowser
import os, os.path, shutil
from os import path
import ast
import time
from collections import OrderedDict

def endpoint_power_extract(endpoint_lst):
    endpoint_line = re.sub(' +',' ',endpoint_lst[-1])
    endpoint_tx, endpoint_rx = endpoint_line.split(" ")[4], endpoint_line.split(" ")[5]
    return [endpoint_tx, endpoint_rx]

def comp_testbed_ideal(ideal_op_id):
    print(ideal_op_id)
    ######Extracting optical data gotten from optics in Cisco switch#############
    opdata_lst = []

    with open('./opdata_pull.json') as fl:
        opdata_pull = fl.read()

    for i in range(opdata_pull.count('\n')):
        opdata_lst.append(ast.literal_eval(opdata_pull.split('\n')[i]))

    #####Use in office##########################################################
    """
    for i in range(opdata_pull.count('\n\n')+1):
        opdata_lst.append(ast.literal_eval(opdata_pull.split('\n\n')[i]))
    """
    ######Extracting optical data gotten from ideal optic in Cisco switch###################
    ideal_op_lst = []
    with open("./idealop.json") as fl:
        ideal_op_pull = fl.read()
    for i in range(ideal_op_pull.count('\n')):
        ideal_op_lst.append(ast.literal_eval(ideal_op_pull.split('\n')[i]))

    #####Divide opdata_Lst and ideal_op_Lst into their dom, idprom and inventory data respectfully
    testbed_dom, testbed_idprom, testbed_inv = opdata_lst[0], opdata_lst[1], opdata_lst[2]
    ideal_dom, ideal_idprom, ideal_inv = ideal_op_lst[0], ideal_op_lst[1], ideal_op_lst[2]
    print(testbed_dom)
    print(testbed_idprom)
    print(testbed_inv)
    print(ideal_dom)
    print(ideal_idprom)
    print(ideal_inv)

    ######storing dictionary containing serial numbers of optics tested in a json file
    id_sn_dict = OrderedDict()
    testbed_inv2 = [re.sub(' +',' ',line) for line in testbed_inv]
    sn_range = [i for i in range(len(testbed_inv2)-1,0,-1) if testbed_inv2[i].strip().startswith('----')][0]

    for line in testbed_inv2[sn_range+1:]:
        id_sn_dict[line.strip().split(' ')[0]] = line.strip().split(' ')[-2]

    with open('tmp_sn_dict.json', 'w') as fl:
        json.dump(id_sn_dict, fl)

    ########Save testbed_idprom and testbed_inv list in "tmp_opdata.json" for generating logs later in 'main'
    opdata = {}
    opdata['idprom'], opdata['inv'] = testbed_idprom, testbed_inv
    opdata = json.dumps(opdata)
    with open("tmp_opdata.json", 'w') as fl:
        fl.write(opdata)


    testbed_viol_dict, err_cnt_dict = OrderedDict(), OrderedDict()
    testbed_viol_dict['dom_viol_dict'], testbed_viol_dict['idprom_viol_dict'], testbed_viol_dict['inv_viol_dict'] = {}, {}, {}
    testbed_viol_dict['dom_viol_dict']['err_cnt'],testbed_viol_dict['inv_viol_dict']['err_cnt'], testbed_viol_dict['idprom_viol_dict']['err_cnt'] = 0,0,0
    testbed_viol_dict['dom_viol_dict']['err_loc'],testbed_viol_dict['inv_viol_dict']['err_loc'], testbed_viol_dict['idprom_viol_dict']['err_loc'] = [],[],[]

    #####Compare data for ideal optic and optics pulled from switch#########################################################################################################################################
    #####compare testbed_dom_lst with ideal_dom###########################################################################
    ideal_dom_lst = []
    tb_dom_ind = [i for i in range(len(testbed_dom)) if testbed_dom[i].startswith('-------')]
    ideal_dom_ind = [i for i in range(len(ideal_dom)) if ideal_dom[i].startswith('-------')]

    for i in range(len(ideal_dom_ind)):
        if i == len(ideal_dom_ind) -1 :
            ind_diff = (ideal_dom_ind[i] - 3) - (ideal_dom_ind[i-1] + 1)
            for ind in range(ideal_dom_ind[i]+1,(ideal_dom_ind[i]+1)+ind_diff):
                ideal_dom_lst.append(ideal_dom[ind].strip())
        else:
            for ind in range(ideal_dom_ind[i]+1,ideal_dom_ind[i+1]-3):
                ideal_dom_lst.append(ideal_dom[ind].strip())

    print('This is tb_dom_ind', tb_dom_ind)
    print('This is ideal_dom_ind', ideal_dom_ind)
    print('This is ideal_dom_lst', ideal_dom_lst)

    for i in range(len(tb_dom_ind)):
        if i == len(tb_dom_ind) -1 :
            ind_diff = (tb_dom_ind[i] - 3) - (tb_dom_ind[i-1] + 1)
            for ind in range(tb_dom_ind[i]+1,(tb_dom_ind[i]+1)+ind_diff):
                if(re.sub(' +',' ',testbed_dom[ind]).strip().split(' ')[2:] != re.sub(' +',' ',ideal_dom_lst[i]).strip().split(' ')[2:]):
                    testbed_viol_dict['dom_viol_dict']['err_loc'].append(ind)
                    testbed_viol_dict['dom_viol_dict']['err_cnt']+=1
        else:
            for ind in range(tb_dom_ind[i]+1,tb_dom_ind[i+1]-3):
                if(re.sub(' +',' ',testbed_dom[ind]).strip().split(' ')[2:] != re.sub(' +',' ',ideal_dom_lst[i]).strip().split(' ')[2:]):
                    testbed_viol_dict['dom_viol_dict']['err_loc'].append(ind)
                    testbed_viol_dict['dom_viol_dict']['err_cnt']+=1
    if testbed_viol_dict['dom_viol_dict']['err_cnt'] > 0:
        testbed_viol_dict['dom_viol_dict']['data'] = testbed_dom

    #######################################################################################################################

    #####compare testbed_idprom with ideal_idprom##########################################################################
    j=0
    for i in range(len(testbed_idprom)):
        if testbed_idprom[i] == '':
            j=0
            continue
        if j==0:
            j+=1
            continue
        if testbed_idprom[i]!=ideal_idprom[j]:
            testbed_viol_dict['idprom_viol_dict']['err_loc'].append(i)
            testbed_viol_dict['idprom_viol_dict']['err_cnt']+=1
        j+=1
    if testbed_viol_dict['idprom_viol_dict']['err_cnt'] > 0:
        testbed_viol_dict['idprom_viol_dict']['data'] = testbed_idprom
    print('This is testbed_viol_dict', testbed_viol_dict)
    ###################################################################################################################################

    #####compare testbed_inv with ideal_inv###################################################################################################################################
    ideal_inv_mod = [re.sub(' +',' ',i) for i in ideal_inv]
    testbed_inv_mod = [re.sub(' +',' ',i) for i in testbed_inv]

    start_ind_tb = [i for i in range(len(testbed_inv)-1,-1,-1) if testbed_inv[i].strip().startswith('-')][0]
    start_ind_id = [i for i in range(len(ideal_inv)-1,-1,-1) if ideal_inv[i].strip().startswith('-')][0]

    for i in range(start_ind_id+1, len(ideal_inv_mod)):
        if ideal_inv_mod[i].strip().startswith('1'):
            ideal_inv_elem = ideal_inv_mod[i]
        ideal_inv_lst = ideal_inv_mod[i].strip().split(' ')
        ideal_inv_lst.pop(0)
        ideal_inv_lst.pop(-2)

    for i in range(start_ind_tb+1, len(testbed_inv_mod)):
        tb_inv_lst = testbed_inv_mod[i].strip().split(' ')
        tb_inv_lst.pop(0)
        tb_inv_lst.pop(-2)
        if tb_inv_lst != ideal_inv_lst:
            testbed_viol_dict['inv_viol_dict']['err_loc'].append(i)
            testbed_viol_dict['inv_viol_dict']['err_cnt']+=1
    if testbed_viol_dict['inv_viol_dict']['err_cnt'] > 0:
        testbed_viol_dict['inv_viol_dict']['data'] = testbed_inv

    print('This is testbed_viol_dict', testbed_viol_dict)
    return testbed_viol_dict

def arista_optical_power_eval(domlst_per_id):
    power_eval = {}
    dom_lst = []
    dom_readout = domlst_per_id
    dom_ind = [i for i in range(len(dom_readout)) if dom_readout[i].startswith('-------')]

    for i in range(len(dom_ind)):
        if i == len(dom_ind) -1 :
            ind_diff = (dom_ind[i] - 3) - (dom_ind[i-1] + 1)
            for ind in range(dom_ind[i]+1,(dom_ind[i]+1)+ind_diff):
                dom_readout_lst = re.sub(' +',' ',dom_readout[ind].strip()).split(' ')
                dom_lst.append(dom_readout_lst)
        else:
            for ind in range(dom_ind[i]+1,dom_ind[i+1]-3):
                dom_readout_lst = re.sub(' +',' ',dom_readout[ind].strip()).split(' ')
                dom_lst.append(dom_readout_lst)

    print('This is dom_lst from op_power_chk', dom_lst)
    ########Pulling temp,volatge,transmit and receive DOM values from dom_lst##############
    power_eval['tempval'],power_eval['voltval'],power_eval['currentval'],power_eval['txval'],power_eval['rxval'] = float(dom_lst[0][1]),float(dom_lst[1][1]),float(dom_lst[2][1]),float(dom_lst[3][1]),float(dom_lst[4][1])
    power_eval['temp_pass'],power_eval['volt_pass'],power_eval['current_pass'],power_eval['tx_pass'],power_eval['rx_pass'] = float(dom_lst[0][3])>float(dom_lst[0][1])>float(dom_lst[0][4]), float(dom_lst[1][3])>float(dom_lst[1][1])>float(dom_lst[1][4]) ,float(dom_lst[2][3])>float(dom_lst[2][1])>float(dom_lst[2][4]), float(dom_lst[3][3])>float(dom_lst[3][1])>float(dom_lst[3][4]),float(dom_lst[4][3])>float(dom_lst[4][1])>float(dom_lst[4][4])
    print(power_eval)
    return power_eval

def gen_oplogs(idprom_opdata_lst, inv_opdata_lst):
    ###comparing idprom data of ideal optic with the optics being tested at the moment and generate log file##
    #idprom_path = './logfiles/prelim_logfiles/idprom_log.txt'
    #inv_path = './logfiles/prelim_logfiles/inv_log.txt'

    if not path.exists('./logfiles/prelim_logfiles/idprom_log.txt'):
        for line in idprom_opdata_lst:
            with open('./logfiles/prelim_logfiles/idprom_log.txt',"a") as fl:
                fl.writelines(line + '\n')
    else:
        os.remove('./logfiles/prelim_logfiles/idprom_log.txt')
        for line in idprom_opdata_lst:
            with open('./logfiles/prelim_logfiles/idprom_log.txt',"a") as fl:
                fl.writelines(line + '\n')

    ###comparing inv data of ideal optic with the optics being tested at the moment and generate log file##
    if not path.exists('./logfiles/prelim_logfiles/inv_log.txt'):
        for line in inv_opdata_lst:
            with open('./logfiles/prelim_logfiles/inv_log.txt', "a") as fl:
                fl.writelines(line + '\n')
    else:
        ###########Delete previous Inventory logs#########################
        os.remove('./logfiles/prelim_logfiles/inv_log.txt')
        for line in inv_opdata_lst:
            with open('./logfiles/prelim_logfiles/inv_log.txt', "a") as fl:
                fl.writelines(line + '\n')
        ###########Delete previous DOM logs#########################
        try:
            os.remove('./logfiles/prelim_logfiles/dom_log.txt')
        except:
            pass
    pass

def gen_oplogs_dom(dom_lst):
    for line in dom_lst:
        with open("./logfiles/prelim_logfiles/dom_log.txt","a") as fl:
            fl.writelines(line + '\n')
    with open("./logfiles/prelim_logfiles/dom_log.txt","a") as fl:
        fl.writelines('\n')
    pass

#########Run app########################
if __name__ == '__main__':
    endpoint_power_extract()
    comp_testbed_ideal()
    cisco_optical_power_eval()
