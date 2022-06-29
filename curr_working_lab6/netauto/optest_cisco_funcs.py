#!/usr/bin/env python3
from ansible_playbook_runner import Runner
from jinja2 import Environment, FileSystemLoader
from io import StringIO
from flask import Flask, render_template, request, session, send_file
import re, json
import sys
import webbrowser
import os, os.path, shutil
from os import path
import ast
import time
from collections import OrderedDict

#################to extract interfaces IDs that are in "UP" and "UP" state######################
def endpoint_power_extract(endpoint_lst):
    endpoint_line = re.sub(' +',' ',endpoint_lst[-1])
    endpoint_tx, endpoint_rx = endpoint_line.split(" ")[-2], endpoint_line.split(" ")[-1]
    return [endpoint_tx, endpoint_rx]

def comp_testbed_ideal(ideal_op_id):
    print(ideal_op_id)
    ######Extracting optical data gotten from optics in Cisco switch#############
    opdata_lst = []

    with open('./opdata_pull.json') as fl:
        opdata_pull = fl.read()
    """
    for i in range(opdata_pull.count('\n')):
        opdata_lst.append(ast.literal_eval(opdata_pull.split('\n')[i]))
    """
    #####Use in office##########################################################

    for i in range(opdata_pull.count('\n\n')+1):
        opdata_lst.append(ast.literal_eval(opdata_pull.split('\n\n')[i]))

    ######Extracting optical data gotten from ideal optic in Cisco switch###################
    ideal_op_lst = []
    with open("./idealop.json") as fl:
        ideal_op_pull = fl.read()
    for i in range(ideal_op_pull.count('\n')):
        ideal_op_lst.append(ast.literal_eval(ideal_op_pull.split('\n')[i]))

    #####Divide opdata_Lst and ideal_op_Lst into their dom, idprom and inventory data respectfully
    testbed_dom, testbed_idprom, testbed_inv = opdata_lst[0], opdata_lst[1:-1], opdata_lst[-1]
    ideal_dom, ideal_idprom, ideal_inv = ideal_op_lst[0], ideal_op_lst[1], ideal_op_lst[-1]

    ######storing dictionary containing serial numbers of optics tested in a json file
    id_sn_dict = OrderedDict()
    testbed_inv2 = [re.sub(' +','',line) for line in testbed_inv]
    sn_range = [i for i in range(len(testbed_inv2)) if testbed_inv2[i].startswith('NAME:"TenGig')]
#    id_sn_dict = [line[line.index('SN:')+3:] for line in inv_lst2[ind[0]:ind[-1]] if 'SN:' in line]
    i = 0
    for line in inv_lst2[sn_range[0]:sn_range[-1]]:
        if 'SN:' in line:
            id_sn_dict[i] = line[line.index('SN:')+3:]
            i+=1
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
    testbed_viol_dict['dom_viol_dict']['err_cnt'],testbed_viol_dict['inv_viol_dict']['err_cnt'] = 0,0
    testbed_viol_dict['dom_viol_dict']['err_loc'],testbed_viol_dict['inv_viol_dict']['err_loc'] = [],[]
    for i in range(len(testbed_idprom)):
        testbed_viol_dict['idprom_viol_dict'][i] = {}
        testbed_viol_dict['idprom_viol_dict'][i]['err_loc'] = []
        testbed_viol_dict['idprom_viol_dict'][i]['err_cnt'] = 0
    #####Compare data for ideal optic and optics pulled from switch#########################################################################################################################################
    #####compare testbed_dom_lst with ideal_dom###########################################################################
    ideal_dom_lst = []
    tb_dom_ind = [testbed_dom.index(i) for i in testbed_dom if i.startswith('---')]
    ideal_dom_ind = [ideal_dom.index(i) for i in ideal_dom if i.startswith('---')]

    for i in range(len(ideal_dom_ind)):
        if i == len(ideal_dom_ind) -1 :
            ind_diff = (ideal_dom_ind[i] - 4) - (ideal_dom_ind[i-1] + 1)
            for ind in range(ideal_dom_ind[i]+1,(ideal_dom_ind[i]+1)+ind_diff):
                ideal_dom_lst.append(ideal_dom[ind])
        else:
            for ind in range(ideal_dom_ind[i]+1,ideal_dom_ind[i+1]-4):
                ideal_dom_lst.append(ideal_dom[ind])

    for i in range(len(tb_dom_ind)):
        if i == len(tb_dom_ind) -1 :
            ind_diff = (tb_dom_ind[i] - 4) - (tb_dom_ind[i-1] + 1)
            for ind in range(tb_dom_ind[i]+1,(tb_dom_ind[i]+1)+ind_diff):
                if(re.sub(' +',' ',testbed_dom[ind]).split(' ')[2:] != re.sub(' +',' ',ideal_dom_lst[i]).split(' ')[2:]):
                    testbed_viol_dict['dom_viol_dict']['err_loc'].append(ind)
                    testbed_viol_dict['dom_viol_dict']['err_cnt']+=1
        else:
            for ind in range(tb_dom_ind[i]+1,tb_dom_ind[i+1]-4):
                if(re.sub(' +',' ',testbed_dom[ind]).split(' ')[2:] != re.sub(' +',' ',ideal_dom_lst[i]).split(' ')[2:]):
                    testbed_viol_dict['dom_viol_dict']['err_loc'].append(ind)
                    testbed_viol_dict['dom_viol_dict']['err_cnt']+=1
    if testbed_viol_dict['dom_viol_dict']['err_cnt'] > 0:
        testbed_viol_dict['dom_viol_dict']['data'] = testbed_dom

    #######################################################################################################################

    #####compare testbed_idprom with ideal_idprom##########################################################################################################################
    j = 0
    for idprom_lst in testbed_idprom:
        serial_index = [ideal_idprom.index(line) for line in ideal_idprom if line.strip().startswith('Vendor Serial No.')][0]
        serial_hash_index = [ideal_idprom.index(line) for line in ideal_idprom if line.strip().startswith('0x0040')][0]
        for i in range(len(idprom_lst)):
            if ((i != serial_index) and (i not in range(serial_hash_index,serial_hash_index+4))):
                try:
                    if idprom_lst[i] != ideal_idprom[i]:
                        testbed_viol_dict['idprom_viol_dict'][j]['err_loc'].append(i)
                        testbed_viol_dict['idprom_viol_dict'][j]['err_cnt']+=1
                except:
                        testbed_viol_dict['idprom_viol_dict'][j]['err_loc'].append(i)
                        testbed_viol_dict['idprom_viol_dict'][j]['err_cnt']+=1
        j+=1

    for i in range(len(testbed_idprom)):
        if testbed_viol_dict['idprom_viol_dict'][i]['err_cnt'] > 0:
            testbed_viol_dict['idprom_viol_dict'][i]['data'] = testbed_idprom[i]

    #####compare testbed_inv with ideal_inv###################################################################################################################################
    print(testbed_inv)
    print(ideal_inv)
    id_prefix = ideal_op_id[0:2] ##get first two digit from ideal id to pull relevant interface inventory data
    print('This is id prefix',id_prefix)
    slash_cnt = ideal_op_id.count('/')
    ideal_op_id_no = ideal_op_id[[ideal_op_id.index(i) for i in ideal_op_id if i.isdigit()][0]:]
    ideal_inv_lst = []
    cnt = 0
    print('This is slash_cnt',slash_cnt)
    print('This is ideal_op_id_no',ideal_op_id_no)
    #####Spliting ideal_inv data into a list - ideal_inv_lst to be compared with the tb_inv_lst#####################
    for id_inv in ideal_inv:
        if cnt == 1:
            for elem in (id_inv.split(',')):
                ideal_inv_lst.append(elem)
            cnt = 0
        else:
            if ideal_op_id_no in id_inv:
                for elem in (id_inv.split(',')):
                    ideal_inv_lst.append(elem)
                cnt = 1
    ideal_inv_lst.pop(0)
    ideal_inv_lst.pop(-1)
    print('This is ideal_inv_lst',ideal_inv_lst)
    ########################################################################
    temp_tb_lst_1,temp_tb_lst_2 = [],[]

    for i in range(len(testbed_inv)):
        if id_prefix in testbed_inv[i].lower() and testbed_inv[i].count('/') == slash_cnt:
            for val_1,val_2 in zip(testbed_inv[i].split(','),testbed_inv[i+1].split(',')):
                temp_tb_lst_1.append(val_1)
                temp_tb_lst_2.append(val_2)
            temp_tb_lst_1.extend(temp_tb_lst_2)
            temp_tb_lst_1.pop(0)
            print('This is temp_tb_lst_1',temp_tb_lst_1)
            if temp_tb_lst_1 != ideal_inv_lst:
                testbed_viol_dict['inv_viol_dict']['err_loc'].append(i)
                testbed_viol_dict['inv_viol_dict']['err_cnt']+=1
            temp_tb_lst_1,temp_tb_lst_2 = [],[]
    if testbed_viol_dict['inv_viol_dict']['err_cnt'] > 0:
        testbed_viol_dict['inv_viol_dict']['data'] = testbed_inv


    return testbed_viol_dict

def cisco_optical_power_eval(domlst_per_id, sw_func, sw_vendor, username, passwd):
    power_eval = {}
    dom_lst = []
    """
    with open('op_power_chk.json') as fl:
        dom_readout = ast.literal_eval(fl.read())
    """
    dom_readout = domlst_per_id
    dom_ind = [dom_readout.index(i) for i in dom_readout if i.startswith('---')]

    for i in range(len(dom_ind)):
        if i == len(dom_ind) -1 :
            ind_diff = (dom_ind[i] - 4) - (dom_ind[i-1] + 1)
            for ind in range(dom_ind[i]+1,(dom_ind[i]+1)+ind_diff):
                dom_val = re.sub(' +',' ',dom_readout[ind])
                dom_val_lst = dom_val.split(' ')
                dom_lst.append(dom_val_lst)
        else:
            for ind in range(dom_ind[i]+1,dom_ind[i+1]-4):
                dom_val = re.sub(' +',' ',dom_readout[ind])
                dom_val_lst = dom_val.split(' ')
                dom_lst.append(dom_val_lst)
    print('This is dom_lst from op_power_chk', dom_lst)
    ########Pulling temp,volatge,transmit and receive DOM values from dom_lst##############
    power_eval['tempval'],power_eval['voltval'],power_eval['txval'],power_eval['rxval'] = float(dom_lst[0][1]),float(dom_lst[1][1]),float(dom_lst[2][1]),float(dom_lst[3][1])
    power_eval['temp_pass'],power_eval['volt_pass'],power_eval['tx_pass'],power_eval['rx_pass'] = float(dom_lst[0][3])>float(dom_lst[0][1])>float(dom_lst[0][4]), float(dom_lst[1][3])>float(dom_lst[1][1])>float(dom_lst[1][4]) ,float(dom_lst[2][3])>float(dom_lst[2][1])>float(dom_lst[2][4]), float(dom_lst[3][3])>float(dom_lst[3][1])>float(dom_lst[3][4])
    print(power_eval)
    return power_eval

def gen_oplogs(idprom_opdata_lst, inv_opdata_lst):
    ###comparing idprom data of ideal optic with the optics being tested at the moment and generate log file##
    #idprom_path = './logfiles/prelim_logfiles/idprom_log.txt'
    #inv_path = './logfiles/prelim_logfiles/inv_log.txt'

    if not path.exists('./logfiles/prelim_logfiles/idprom_log.txt'):
        for i in range(len(idprom_opdata_lst)):
            for j in range(len(idprom_opdata_lst[i])):
                with open('./logfiles/prelim_logfiles/idprom_log.txt',"a") as fl:
                    if j != len(idprom_opdata_lst[i]) -1:
                        fl.writelines(idprom_opdata_lst[i][j] + '\n')
                    if j == len(idprom_opdata_lst[i]) -1:
                        fl.writelines(idprom_opdata_lst[i][j] + '\n')
                        fl.writelines('\n')


    else:
        os.remove('./logfiles/prelim_logfiles/idprom_log.txt')
        for i in range(len(idprom_opdata_lst)):
            for j in range(len(idprom_opdata_lst[i])):
                with open('./logfiles/prelim_logfiles/idprom_log.txt',"a") as fl:
                    if j != len(idprom_opdata_lst[i]) -1:
                        fl.writelines(idprom_opdata_lst[i][j] + '\n')
                    if j == len(idprom_opdata_lst[i]) -1:
                        fl.writelines(idprom_opdata_lst[i][j] + '\n')
                        fl.writelines('\n')
    ###comparing inv data of ideal optic with the optics being tested at the moment and generate log file##
    if not path.exists('./logfiles/prelim_logfiles/inv_log.txt'):
        for line in inv_opdata_lst:
            with open('./logfiles/prelim_logfiles/inv_log.txt', "a") as fl:
                fl.writelines(line + '\n')

    else:
        ###########Delete previous DOM logs#########################
        try:
            os.remove('./logfiles/prelim_logfiles/dom_log.txt')
        except:
            pass
        ###########Delete previous Inventory logs#########################
        os.remove('./logfiles/prelim_logfiles/inv_log.txt')
        for line in inv_opdata_lst:
            with open('./logfiles/prelim_logfiles/inv_log.txt', "a") as fl:
                fl.writelines(line + '\n')
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
