#!/usr/bin/env python3
from ansible_playbook_runner import Runner
from jinja2 import Environment, FileSystemLoader
from io import StringIO
from flask import Flask, render_template, request, session, send_file
import endpoint_pbrun, idealop_pbrun, optest_junos_funcs, optest_cisco_funcs, optest_arista_funcs
import multiprocessing as mp
import re
import sys
import webbrowser
import os, os.path
from os import path
import ast
import time
import json

cnt1 = 0 #counter to prevent running - playbook to pull MAC address of endpoint1 switch multiple times.
cnt2 = 0 #counter to prevent running - playbook to pull MAC address of endpoint2 switch multiple times.

def port_extract(lldp_neighbor_lst, sw_vendor_end):
    if sw_vendor_end == 'juniper':
        port_id = [line[line.index(':')+1:].strip().strip('"') for line in lldp_neighbor_lst if 'port description' in line.lower()][0]
        if port_id.endswith('.0'):
            port_id = port_id.strip('.0')
    if sw_vendor_end == 'arista':
        lldp_neighbor_lst = [re.sub(' +','',line.lower()) for line in lldp_neighbor_lst]
        port_id = [line[line.index(':')+1:].strip('"') for line in lldp_neighbor_lst if line.startswith('portid:')][0]
    if sw_vendor_end == 'cisco':
        lldp_neighbor_lst = [re.sub(' +','',line.lower()) for line in lldp_neighbor_lst]
        port_id = [line[line.index(':')+1:].strip('"') for line in lldp_neighbor_lst if line.startswith('portid:')][0]
    return port_id

def endpoint1(lldp_neighbor_portid, sw_func, sw_vendor):
    with open('tmp_auth_dict.json') as fl:
        auth_dict = ast.literal_eval(fl.read().strip())
        end1_path = auth_dict['End1']['ansi_path']
        sw_func, sw_vendor, username, passwd = auth_dict['End1']['sw_func'], auth_dict['End1']['sw_vendor'], auth_dict['End1']['usrname'], auth_dict['End1']['pass']
    ###########################Endpoint1##############################################################################################
    print('This is lldp_neighbor_portid', lldp_neighbor_portid)
    endpoint1_power = {}
    ########Run endpoint1_playb.yml to pull the TX and RX powers for the endpoint optic with variable name "endp_int" entered by user in the "user_inp" flask page#############
    env = Environment(loader=FileSystemLoader('.'))
    templ = env.get_template(end1_path +  "/endpoint1_playb.j2")

    with open(end1_path + "/endpoint1_playb.yml", "w") as fl:
        fl.write(templ.render(endp_int1=lldp_neighbor_portid, sw_func=sw_func, sw_vendor=sw_vendor, username=username, passwd=passwd))

    pbrun = Runner([end1_path + '/inventory/inven.ini'], end1_path + '/endpoint1_playb.yml')
    res = pbrun.run()

    try:
        if sw_vendor == 'juniper':
            with open("./endpoint1.txt","r") as fl:
                endpoint1_dat = fl.read()
                #####Convert string of dictionary as read from file to the actual dictionary
                endpoint1_dict = ast.literal_eval(endpoint1_dat)
                ##################String splicing to get TX and RX optest_dicts from endpoint switch
                endpoint1_lst = endpoint1_dict['stdout_lines']
                endpoint1_lst = [i.strip(' ') for i in endpoint1_lst]
                endpoint1_lst = [re.sub(' +',' ',i) for i in endpoint1_lst]

                for data in endpoint1_lst:
                    if data.startswith('Laser output power :'):
                        endpoint1_power['endpoint_tx'] = float(re.findall(r'[-+]?\d*\.?\d+|\d+', data)[1])
                    if data.startswith('Receiver signal average optical power :'):
                        endpoint1_power['endpoint_rx'] = float(re.findall(r'[-+]?\d*\.?\d+|\d+', data)[1])
            return endpoint1_power

        if sw_vendor == 'cisco':
            with open("./endpoint1.json") as fl:
                endpoint1_lst = ast.literal_eval(fl.read().strip())
                endpoint_extract_lst = optest_cisco_funcs.endpoint_power_extract(endpoint1_lst)
                endpoint1_power['endpoint_tx'] = float(endpoint_extract_lst[0])
                endpoint1_power['endpoint_rx'] = float(endpoint_extract_lst[1])
            return endpoint1_power

        if sw_vendor == 'arista':
            with open("./endpoint1.json") as fl:
                endpoint1_lst = ast.literal_eval(fl.read().strip())
                endpoint_extract_lst = optest_arista_funcs.endpoint_power_extract(endpoint1_lst)
                endpoint1_power['endpoint_tx'] = float(endpoint_extract_lst[0])
                endpoint1_power['endpoint_rx'] = float(endpoint_extract_lst[1])
            return endpoint1_power

    except:
        endpoint1_power['endpoint_tx'] = ''
        endpoint1_power['endpoint_rx'] = ''

    #######################end Endpoint1##############################################################

def endpoint2(lldp_neighbor_portid, sw_func, sw_vendor):
    with open('tmp_auth_dict.json') as fl:
        auth_dict = ast.literal_eval(fl.read().strip())
        end2_path = auth_dict['End2']['ansi_path']
        sw_func, sw_vendor, username, passwd = auth_dict['End2']['sw_func'], auth_dict['End2']['sw_vendor'], auth_dict['End2']['usrname'], auth_dict['End2']['pass']
    ###########################Endpoint2##############################################################################################
    print('This is lldp_neighbor_portid', lldp_neighbor_portid)
    endpoint2_power = {}
    ########Run endpoint2_playb.yml to pull the TX and RX powers##############
    env = Environment(loader=FileSystemLoader('.'))
    templ = env.get_template(end2_path +"/endpoint2_playb.j2")

    with open(end2_path + "/endpoint2_playb.yml", "w") as fl:
        fl.write(templ.render(endp_int2=lldp_neighbor_portid, sw_func=sw_func, sw_vendor=sw_vendor, username=username, passwd=passwd))

    pbrun = Runner([end2_path + '/inventory/inven.ini'], end2_path + '/endpoint2_playb.yml')
    res = pbrun.run()

    try:
        if sw_vendor == 'juniper':
            with open("./endpoint2.txt","r") as fl:
                endpoint2_dat = fl.read()
                #####Convert string of dictionary as read from file to the actual dictionary
                endpoint2_dict = ast.literal_eval(endpoint2_dat)
                ##################String splicing to get TX and RX optest_dicts from endpoint switch
                endpoint2_lst = endpoint2_dict['stdout_lines']
                endpoint2_lst = [i.strip(' ') for i in endpoint2_lst]
                endpoint2_lst = [re.sub(' +',' ',i) for i in endpoint2_lst]

                for data in endpoint2_lst:
                    if data.startswith('Laser output power :'):
                        endpoint2_power['endpoint_tx'] = float(re.findall(r'[-+]?\d*\.?\d+|\d+', data)[1])
                    if data.startswith('Receiver signal average optical power :'):
                        endpoint2_power['endpoint_rx'] = float(re.findall(r'[-+]?\d*\.?\d+|\d+', data)[1])
                return endpoint2_power

        if sw_vendor == 'cisco':
            with open("./endpoint2.json") as fl:
                endpoint2_lst = ast.literal_eval(fl.read().strip())
                endpoint_extract_lst = optest_cisco_funcs.endpoint_power_extract(endpoint2_lst)
                endpoint2_power['endpoint_tx'] = float(endpoint_extract_lst[0])
                endpoint2_power['endpoint_rx'] = float(endpoint_extract_lst[1])
            return endpoint2_power

        if sw_vendor == 'arista':
            with open("./endpoint2.json") as fl:
                endpoint2_lst = ast.literal_eval(fl.read().strip())
                endpoint_extract_lst = optest_arista_funcs.endpoint_power_extract(endpoint2_lst)
                endpoint2_power['endpoint_tx'] = float(endpoint_extract_lst[0])
                endpoint2_power['endpoint_rx'] = float(endpoint_extract_lst[1])
            return endpoint2_power

    except:
        endpoint1_power['endpoint_tx'] = ''
        endpoint1_power['endpoint_rx'] = ''

        #######################end Endpoint2#############################################################

def endpoint_pbrun(port_id):
    ###########################################################################
    with open('tmp_auth_dict.json') as fl:
        auth_dict = ast.literal_eval(fl.read().strip())

    tb_path = auth_dict['TB']['ansi_path']
    sw_func, sw_vendor, username, passwd, sw_vendor_end1, sw_vendor_end2 = auth_dict['TB']['sw_func'], auth_dict['TB']['sw_vendor'], auth_dict['TB']['usrname'], auth_dict['TB']['pass'], auth_dict['End1']['sw_vendor'], auth_dict['End2']['sw_vendor']
    ############################################################################
    with open('tmp_auth_dict.json') as fl:
        auth_dict = ast.literal_eval(fl.read().strip())
    #########reading endp1_mac and endp2_mac from 'endp_macs.txt'
    with open('endp_macs.json', 'r') as fl:
        endp_macs = json.load(fl)
    endp1_mac = endp_macs['endp1_mac']
    endp2_mac = endp_macs['endp2_mac']

    #########Playbook to pull MAC address of the endpoint optics########
    endpoint_power = {}

    ##########Define Playbook to find the lldp neighbor of optic currently in test########
    env = Environment(loader=FileSystemLoader('.'))
    templ = env.get_template(tb_path + "/lldp_neighbor_pbrun.j2")

    if sw_vendor == 'juniper':
        ansi_pb_path = tb_path + r"/lldp_neighbor_pbrun_"+port_id[7:]+".yml"

        with open(ansi_pb_path, "w") as fl:
            fl.write(templ.render(port_id=port_id, sw_func=sw_func, sw_vendor=sw_vendor, username=username, passwd=passwd))

        pbrun = Runner([tb_path + '/inventory/inven.ini'], ansi_pb_path)
        res = pbrun.run()

    if sw_vendor == 'cisco':
        id = port_id.replace('/','_')
        ansi_pb_path = tb_path + r"/lldp_neighbor_pbrun_"+id+".yml"

        with open(ansi_pb_path, "w") as fl:
            fl.write(templ.render(port_id=port_id, sw_func=sw_func, sw_vendor=sw_vendor, username=username, passwd=passwd))

        pbrun = Runner([tb_path + '/inventory/inven.ini'], ansi_pb_path)
        res = pbrun.run()
        #os.remove(ansi_pb_path)

    if sw_vendor == 'arista':
        ansi_pb_path = tb_path + r"/lldp_neighbor_pbrun_"+port_id+".yml"

        with open(ansi_pb_path, "w") as fl:
            fl.write(templ.render(port_id=port_id, sw_func=sw_func, sw_vendor=sw_vendor, username=username, passwd=passwd))

        pbrun = Runner([tb_path + '/inventory/inven.ini'], ansi_pb_path)
        res = pbrun.run()


    with open('./lldp_neighbor.json') as fl:
        lldp_neighbor = fl.read().strip()
        lldp_neighbor_lst = ast.literal_eval(lldp_neighbor)
        lldp_neighbor_lst = [re.sub(' +',' ',i.strip()) for i in lldp_neighbor_lst]
        print('This is lldp_neighbor_lst', lldp_neighbor_lst)

        t0 = time.time()##start time

        lldp_neighbor_mac = [line[line.index(':')+1:].strip() for line in lldp_neighbor_lst if line.lower().startswith('chassis id')][0]
        print('this is lldp_neighbor_mac', lldp_neighbor_mac)
        print('this is endp1_mac', endp1_mac)
        print('this is endp2_mac', endp2_mac)

        try:
            if endp1_mac.replace(':','').replace('.','')[:10] == lldp_neighbor_mac.replace(':','').replace('.','')[:10]:
                print('this is sw_vendor_end1', sw_vendor_end1)
                lldp_neighbor_portid = port_extract(lldp_neighbor_lst, sw_vendor_end1)
                endpoint_power = endpoint1(lldp_neighbor_portid, sw_func, sw_vendor)
                print('This is endpoint_power', endpoint_power)
                t1 = time.time()##end time
                print('enpoint run Duration: {:.4f}'.format(t1 - t0))
                #########Run app########################
                print (lldp_neighbor_portid, lldp_neighbor_mac, endp1_mac, endp2_mac, endpoint_power)
                return endpoint_power

            if endp2_mac.replace(':','').replace('.','')[:10] == lldp_neighbor_mac.replace(':','').replace('.','')[:10]:
                print('this is sw_vendor_end1', sw_vendor_end2)
                lldp_neighbor_portid = port_extract(lldp_neighbor_lst, sw_vendor_end2)
                endpoint_power = endpoint2(lldp_neighbor_portid, sw_func, sw_vendor)
                print('This is endpoint_power', endpoint_power)
                t1 = time.time()##end time
                print('enpoint run Duration: {:.4f}'.format(t1 - t0))
                #########Run app########################
                print (lldp_neighbor_portid, lldp_neighbor_mac, endp1_mac, endp2_mac, endpoint_power)
                return endpoint_power
        except:
            return endpoint_power

        """

        for line in lldp_neighbor_lst:
            try:
                if endp1_mac.replace(':','').replace('.','') == line[line.index(':')+1:].strip().replace(':','').replace('.',''):
                    lldp_neighbor_portid = port_extract(lldp_neighbor_lst, sw_vendor_end1)
                    endpoint_power = endpoint1(lldp_neighbor_portid, sw_func, sw_vendor)
                    print('This is endpoint_power', endpoint_power)
                    t1 = time.time()##end time
                    print('enpoint run Duration: {:.4f}'.format(t1 - t0))
                    #########Run app########################
                    print (lldp_neighbor_portid, lldp_neighbor_mac, endp1_mac, endp2_mac, endpoint_power)
                #
                if endp2_mac.replace(':','').replace('.','') == line[line.index(':')+1:].strip().replace(':','').replace('.',''):
                    lldp_neighbor_portid = port_extract(lldp_neighbor_lst, sw_vendor_end2)
                    endpoint_power = endpoint2(lldp_neighbor_portid, sw_func, sw_vendor)
                    print('This is endpoint_power', endpoint_power)
                    t1 = time.time()##end time
                    print('enpoint run Duration: {:.4f}'.format(t1 - t0))
                    #########Run app########################
                    print (lldp_neighbor_portid, lldp_neighbor_mac, endp1_mac, endp2_mac, endpoint_power)
                return endpoint_power
            except:
                continue
        """


def endpoint_mac_pull():
    ###MAC pull for endpoint1######
    with open('tmp_auth_dict.json') as fl:
        auth_dict = ast.literal_eval(fl.read().strip())
    try:
        end_path = auth_dict['End1']['ansi_path']
        username = auth_dict['End1']['usrname']
        passwd = auth_dict['End1']['pass']
        sw_func, sw_vendor = auth_dict['End1']['sw_func'], auth_dict['End1']['sw_vendor']

        print('auth_dict inside of func() ',auth_dict)
        print('end_path ', end_path)
        env = Environment(loader=FileSystemLoader('.'))
    #    ansiblefiles\junos_ansiblefil\endp1_macpull_pbrun.j2
        templ = env.get_template(end_path + "/endp1_macpull_pbrun.j2")
        with open(end_path + '/endp1_macpull_pbrun.yml', 'w') as fl:
            fl.write(templ.render(username=username, passwd=passwd, sw_func=sw_func, sw_vendor=sw_vendor))
        print(end_path + '/inventory/inven.ini','\n',end_path + '/endp1_macpull_pbrun.yml')
        pbrun = Runner([end_path + '/inventory/inven.ini'], end_path + '/endp1_macpull_pbrun.yml')
        res = pbrun.run()

        #############################################################################################################
        if sw_vendor == 'juniper':
            with open("./endp1_mac.json") as fl:
                endp1_det = ast.literal_eval(fl.read().strip())
                endp1_det_lst = [re.sub(' +',' ',i.strip()) for i in endp1_det] ####Removing white spaces
                endp1_mac = [val for val in endp1_det_lst if val.lower().startswith("public base address") or val.lower().startswith("base address")][0]
                endp1_mac = endp1_mac[-17:len(endp1_mac)]
                print('This is endp1_mac',endp1_mac)
        if sw_vendor == 'arista':
            with open("./endp1_mac.json") as fl:
                endp1_det = ast.literal_eval(fl.read().strip())
                for line in endp1_det:
                    line = re.sub(' +','',line)
                    if line.startswith('ChassisID:'):
                        endp1_mac = line[line.index(':')+1:]
        if sw_vendor == 'cisco':
            with open("./endp1_mac.json") as fl:
                endp1_mac_lst = ast.literal_eval(fl.read().strip())
            ##to get endp1_mac to like this '0008.e3ff.fc00' as an example.
            for line in endp1_mac_lst:
            	if 'static' in line:
            		endp1_mac = re.sub(' +',' ',line.strip()).split(',')[0].split(' ')[1]
                    ####to get endp1_mac to like '0008e3fffc00' as an example.
                #    endp1_mac = endp1_mac.replace('.','')

    except:
        endp1_mac = ""

    ###MAC pull for endpoint2######
    try:
        end_path = auth_dict['End2']['ansi_path']
        username = auth_dict['End2']['usrname']
        passwd = auth_dict['End2']['pass']
        sw_func, sw_vendor = auth_dict['End2']['sw_func'], auth_dict['End2']['sw_vendor']

        print('auth_dict inside of func() ',auth_dict)
        print('end_path ', end_path)
        env = Environment(loader=FileSystemLoader('.'))
    #    ansiblefiles\junos_ansiblefil\endp1_macpull_pbrun.j2
        templ = env.get_template(end_path + "/endp2_macpull_pbrun.j2")
        with open(end_path + '/endp2_macpull_pbrun.yml', 'w') as fl:
            fl.write(templ.render(username=username, passwd=passwd, sw_func=sw_func, sw_vendor=sw_vendor))
        pbrun = Runner([end_path + '/inventory/inven.ini'], end_path + '/endp2_macpull_pbrun.yml')
        res = pbrun.run()

        ##########################################################################################################
        if sw_vendor == 'juniper':
            with open("./endp2_mac.json") as fl:
                endp2_det = ast.literal_eval(fl.read().strip())
                endp2_det_lst = [re.sub(' +',' ',i.strip()) for i in endp2_det] ####Removing white spaces
                endp2_mac = [val for val in endp2_det_lst if val.lower().startswith("public base address") or val.lower().startswith("base address")][0]
                endp2_mac = endp2_mac[-17:len(endp2_mac)]
                print('This is endp2_mac',endp2_mac)
        if sw_vendor == 'arista':
            with open("./endp2_mac.json") as fl:
                endp2_det = ast.literal_eval(fl.read().strip())
                for line in endp2_det:
                    line = re.sub(' +','',line)
                    if line.startswith('ChassisID:'):
                        endp2_mac = line[line.index(':')+1:]

        if sw_vendor == 'cisco':
            with open("./endp2_mac.json") as fl:
                endp2_mac_lst = ast.literal_eval(fl.read().strip())
            ##to get endp1_mac to like this '0008.e3ff.fc00' as an example.
            for line in endp2_mac_lst:
            	if 'static' in line:
            		endp2_mac = re.sub(' +',' ',line.strip()).split(',')[0].split(' ')[1]
                    ####to get endp1_mac to like '0008e3fffc00' as an example.
                    #endp2_mac = endp2_mac.replace('.','')

    except:
        endp2_mac = ""

    ####################save endp1_mac() and endp2_mac() in a txt_file for use later in the program#################
    endp_macs = {}
    endp_macs['endp1_mac'] = endp1_mac
    endp_macs['endp2_mac'] = endp2_mac
    endp_macs = json.dumps(endp_macs)

    with open('endp_macs.json', 'w') as fl:
        fl.write(endp_macs)

    pass


"""
def main():
    with open('tmp_auth_dict.json') as fl:
        auth_dict = ast.literal_eval(fl.read().strip())
        print('auth_dict outside of func() ',auth_dict)
    endpoint_mac_pull()
    endpoint_pbrun()
"""
if __name__ == '__main__':
    cnt1 = 0 #counter to prevent running - playbook to pull MAC address of endpoint1 switch multiple times.
    cnt2 = 0 #counter to prevent running - playbook to pull MAC address of endpoint2 switch multiple times.
    endpoint_mac_pull()
    endpoint_pbrun()
