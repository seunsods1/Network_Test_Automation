#!/usr/bin/env python3
from ansible_playbook_runner import Runner
from jinja2 import Environment, FileSystemLoader
from io import StringIO
from flask import Flask, render_template, request, session, send_file
import re
import sys
import webbrowser
import os, os.path, shutil
from os import path
import ast
import time
from collections import OrderedDict

#################to extract interfaces IDs that are in "UP" and "UP" state######################
def int_extractor(interface, ideal_op_id):
    interface = [re.sub(' +',' ',i) for i in interface]
    lst = []
    for i in range(len(interface)):
        if len(interface[i].strip().split(" ")) == 3:
            if (interface[i].strip().split(" ")[1] and interface[i].strip().split(" ")[2]) == "up":
                if (interface[i].strip().split(" ")[0][0:7] == ideal_op_id[0:7]):
                    lst.append(interface[i].strip().split(" ")[0])
    return lst
    """
    interface = [re.sub(' +',' ',i) for i in interface]
    lst = []
    for i in range(len(interface)):
    	if len(interface[i].strip().split(" ")) == 3:
    		if (interface[i].strip().split(" ")[1] and interface[i].strip().split(" ")[2]) == "up":
    			if(interface[i].startswith("ge") or interface[i].startswith("xe") or interface[i].startswith("et")):
    				lst.append(interface[i].strip().split(" ")[0])
    return lst
    """
def dom_val_extractor(dom_lst, index):
    optest_dict = dom_lst[index]
    colon_index = optest_dict.strip().find(':')+1
    result = optest_dict[colon_index:].lstrip()
    return result

def index_gen(dom_lst, keyword):
    ind = [i for i in range(len(dom_lst)) if dom_lst[i][:dom_lst[i].find(':')].strip(' ') == keyword][0]
    return ind

def dom_parse(dom_lst, op_ser_num):
#    return dom_lst
    #############Removing leading and trailling spaces#################
    dom_lst = [i.strip(' ') for i in dom_lst]
    ###############Removing unnecesary spaces amongst list elements##########
    dom_lst = [re.sub(' +',' ',i) for i in dom_lst]
    ###################Extracting Idprom vals from juniper's DOM cmd#######
    dom_dict = {}
    id_keywords = {'tempval':'Module temperature','hightempthresh':'Module temperature high warning threshold','lowtempthresh':'Module temperature low warning threshold','voltval':'Module voltage','highvoltthres':'Module voltage high warning threshold','lowvoltthres':'Module voltage low warning threshold','txval':'Laser output power','txhighthres':'Laser output power high warning threshold','txlowthres':'Laser output power low warning threshold','rxval':'Receiver signal average optical power','rxhighthres':'Laser rx power high warning threshold','rxlowthres':'Laser rx power low warning threshold'}
    for k,v in id_keywords.items():
        dom_index = index_gen(dom_lst, v)
        dom_val = dom_val_extractor(dom_lst, dom_index)
        dom_dict[k] = dom_val
    dom_dict['serial_num'] = op_ser_num
    return dom_dict


   # print(idprom_val,'\n','\n','\n','\n',idprom_lst,'\n','\n','\n','\n',idprom_dict)

def opdata_eval(optest_dict):
    eval_res = []
    evalres = {}
    temp_dict,volt_dict,tx_dict,rx_dict = {},{},{},{}
    temp_dict['temp'],volt_dict['volt'],tx_dict['tx'],rx_dict['rx']={},{},{},{}
    #store result of dom check in dom check dictionary#
    dom_check = {}

    def extract_int(str_val):
        int_val = re.findall(r'[-+]?\d*\.?\d+|\d+', str_val)[0]
        return int_val

    def keyword_ext(k, optest_dict):
        tem = {}
        if 'high' in k:
                tem['high'] = extract_int(optest_dict[k])
        if 'low' in k:
                tem['low'] = extract_int(optest_dict[k])
        if 'val' in k:
                tem['val'] = extract_int(optest_dict[k])
        return tem

    for k,v in optest_dict.items():
        if 'temp' in k:
            temp_dict['temp'].update(keyword_ext(k,optest_dict))
        if 'volt' in k:
            volt_dict['volt'].update(keyword_ext(k,optest_dict))
        if 'tx' in k:
            tx_dict['tx'].update(keyword_ext(k,optest_dict))
        if 'rx' in k:
            rx_dict['rx'].update(keyword_ext(k,optest_dict))
    evalres.update(temp_dict)
    evalres.update(volt_dict)
    evalres.update(tx_dict)
    evalres.update(rx_dict)

    ####return pass if requirements met for temp, volt, tx and rx##
    dom_check['temp_pass'] = float(evalres['temp']['low']) < float(evalres['temp']['val']) < float(evalres['temp']['high'])
    dom_check['volt_pass'] = float(evalres['volt']['low']) < float(evalres['volt']['val']) < float(evalres['volt']['high'])
    dom_check['tx_pass'] = float(evalres['tx']['low']) < float(evalres['tx']['val']) < float(evalres['tx']['high'])
    dom_check['rx_pass'] = float(evalres['rx']['low']) < float(evalres['rx']['val']) < float(evalres['rx']['high'])

    return dom_check


def gen_oplogs_dom(dom_lst):
    for line in dom_lst:
        with open("./logfiles/prelim_logfiles/dom_log.txt","a") as fl:
            fl.writelines(line + '\n')

"""
def gen_oplogs_dom(dom_lst,port_id):
#    dom_lst = ast.literal_eval(dom_lst)
    for line in dom_lst:
        dom_log_path = "./logfiles/dom_log" + port_id[7:] + ".txt"
        with open(dom_log_path,"a") as fl:
            fl.writelines(line + '\n')
"""
"""
def combine_gen_oplogs_dom(interface_lst):
    print(interface_lst)
    with open("./logfiles/dom_log.txt", 'a') as fl:
        for port in interface_lst:
            print(port)
            dom_log_path = "./logfiles/dom_log" + port[7:] + ".txt"
            with open(dom_log_path, 'r') as fil:
                fl.write(fil.read())
                fl.write('\n')
"""



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

#def comp_testbed_ideal(optest_dict, ideal_op, dom_opresult_dict, idprom_opresult_dict, inv_opresult_dict, interface_lst, jun_idprom_cmd):
def comp_testbed_ideal(idealop, dom_opdata_lst, idprom_opdata_lst, inv_opdata_lst):
    ###############Extract DOM, IDPROM and Inventory data from idealop###################
    ideal_op_dom = ast.literal_eval(idealop.split("\n")[0])
    ideal_op_idprom = ast.literal_eval(idealop.split("\n")[1])
    ideal_op_inv = ast.literal_eval(idealop.split("\n")[2])

    ############compare ideal optic's DOM data (ideal_op_dom) with that of each of the optics (dom_opdata_lst)
    dom_violation_dict = OrderedDict()
    cnt = 0
    err_cnt = OrderedDict()
    err_cnt['idprom_err_cnt'], err_cnt['inv_err_cnt'], err_cnt['dom_err_cnt'] = OrderedDict(),OrderedDict(),OrderedDict()
#    end_ind = len(ideal_op_dom)
    for i in range(0,len(dom_opdata_lst),len(ideal_op_dom)):
        end_ind = i+len(ideal_op_dom)
        ind = 'port '+ str(cnt)
        dom_read_range =  i+7
        err_loc = []
        for line in range(i, end_ind):
            if (line not in range(dom_read_range) and line != i+24 and line != i+26):
                if (dom_opdata_lst[line] != ideal_op_dom[line-i]):
                    err_loc.append(line-i)

        #################New change###################################################
        dom_violation_dict[ind] = OrderedDict()
        dom_violation_dict[ind]['err_cnt'] = len(err_loc)
        dom_violation_dict[ind]['err_loc'] = err_loc
        ##############################################################################
        if (len(err_loc) > 0):
            dom_violation_dict[ind]['data'] = dom_opdata_lst[i:end_ind]
            err_cnt['dom_err_cnt'][ind] = OrderedDict()
            err_cnt['dom_err_cnt'][ind] = len(err_loc)
        cnt += 1



     ############compare ideal optic's IDPROM data (ideal_op_idprom) with that of each of the optics (idprom_opdata_lst)
    idprom_violation_dict = OrderedDict()
    idprom_violation_dict['err_loc'] = []
    idprom_opdata_lst2 = [re.sub(' +',' ',i) for i in idprom_opdata_lst]
    ideal_op_idprom2 = [re.sub(' +',' ',i) for i in ideal_op_idprom]

    for i in range(10,len(idprom_opdata_lst2)):
        if (idprom_opdata_lst2[i].strip(" ").split(" ")[1:] != ideal_op_idprom2[10].strip(" ").split(" ")[1:]):
                    idprom_violation_dict['err_loc'].append(i)
    #################New change###################################################
    idprom_violation_dict['err_cnt'] = len(idprom_violation_dict['err_loc'])
    ##############################################################################
    if len(idprom_violation_dict['err_loc']) > 0:
            idprom_violation_dict['data'] = []
            idprom_violation_dict['data'].append(idprom_opdata_lst)
            err_cnt['idprom_err_cnt'] = len(idprom_violation_dict['err_loc'])

    ############compare ideal optic's Inventory data (ideal_op_inv) with that of each of the optics (inv_opdata_lst)
    inv_violation_dict = OrderedDict()
    inv_violation_dict['err_loc'] = []

    inv_opdata_lst2 = [re.sub(' +',' ',i) for i in inv_opdata_lst]
    ideal_op_inv = [re.sub(' +',' ',i) for i in ideal_op_inv]

    inter_ind_lst = [inv_opdata_lst2.index(i) for i in inv_opdata_lst2 if i.strip().startswith('Xcvr')]
    id_inv_ind = [ideal_op_inv.index(i) for i in ideal_op_inv if i.strip().startswith('Xcvr')][0]

    for i in inter_ind_lst:
            testbed_inv = inv_opdata_lst2[i].strip().split()
            ideal_inv = ideal_op_inv[id_inv_ind].strip().split()
            testbed_inv.pop(1),testbed_inv.pop(-2)
            ideal_inv.pop(1), ideal_inv.pop(-2)
            if (testbed_inv != ideal_inv):
                    inv_violation_dict['err_loc'].append(i)
    #################New change###################################################
    inv_violation_dict['err_cnt'] = len(inv_violation_dict['err_loc'])
    ##############################################################################
    if (len(inv_violation_dict['err_loc']) > 0):
            inv_violation_dict['data'] = []
            inv_violation_dict['data'] = inv_opdata_lst
            err_cnt['inv_err_cnt'] = len(inv_violation_dict['err_loc'])
    ###########Dictionary to hold all optical data violations###########################
    opdata_viol_dict = OrderedDict()
    opdata_viol_dict['dom_viol_dict'] = dom_violation_dict
    opdata_viol_dict['idprom_viol_dict'] = idprom_violation_dict
    opdata_viol_dict['inv_viol_dict'] = inv_violation_dict

    return opdata_viol_dict

#########Run app########################
if __name__ == '__main__':
    int_extractor()
    dom_val_extractor()
    index_gen()
    idprom_parse()
    inv_parse()
    dom_parse()
    opdata_eval()
    idprom_dat_eval()
    gen_oplogs()
    comp_testbed_ideal()
