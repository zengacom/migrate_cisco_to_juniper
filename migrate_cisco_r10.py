#naam: migrate_cisco
#versie: t9
#datum: 28-3-2018
#owner: Hessel Idzenga / 06 319 51897
#release history:
# r1 21-11-2017 initiele versie
# r2 5-12-2017  aanhalingstekens rond description; bridge domain 4000 en 4001 bij PE poorten met CPE
# r3 7-12-2017  aparte behandeling voor vlans 4020 en 4021 voor UNET-NO-CPE management
# r4 7-2-2018   fout gevonden in output creatie voor vlan 4000 of vlan 4001
# r5 7-2-2018   fout gevonden in situatie als remote vfi wel aanwezig maar geen neighbors heeft;
#               Access vlan port  procedure aangepast:
#               * unit 0 ipv unit vlan_id
#               * doorgaan ook als er geen description op de interfaces staat
# r6 14-2-2018  correctie van de situatie dat er geen routing-instance wordt aangemaakt als de VLAN
#               op Cisco geen vlan description heeft
# r7 26-2-2018  output naar ACX50xx er bij gemaakt. Die wijkt af op details, specifiek vlan 4000, 4001
#               vlan 4000, 4001, 4020, 4021
# r8 19-3-2018  foutje in het zoeken van het ip adres van de source PE. Als je die in hoofdletters schrijft
#               in mapping.txt wordt hij niet gevonden in de lijst met loopbacks: filenaam is lowercase
# r9 28-3-2018  bij ACX moet de class-of-service op de volledige interface worden gezet, niet op de vlan / unit
#               waarop de service wordt afgeleverd
# r10 28-5-2018 bij een vlan range (1950-1955) die wordt geexpandeerd naar losse VLANs werkte de telling niet goed
#               omdat een item werd verwijderd uit een lijst, en de teller dus een positie te ver stond en een
#               VLAN vergat


from os import listdir, chdir, walk
import sys

def log(s):
    logfile.write(s+'\n')

def create_loopbacks():
    log('loopbacklijst maken')
    mypath = "alle_PE"
    loopbacklijst = {}
    f = []
    for (dirpath, dirnames, filenames) in walk(mypath):
        f.extend(filenames)
    chdir(mypath)    
    for filename in f:
#        print('zoek loopback in '+ filename+'\n')
        config = open(filename)
        inhoud = config.read().split('\n')
        if 'interface Loopback0' in inhoud:
            # nu is het een Cisco
            loopback_regel = inhoud.index('interface Loopback0')+1
            while not inhoud[loopback_regel].startswith(' ip address'):
                loopback_regel +=1
            regel_list= inhoud[loopback_regel].split(' ')
            ip_address = regel_list[3]
            loopbacklijst[ip_address] = filename
        else:
            found =False
            index = 0
            length = len(inhoud)
            while not found and index < length:
                found = inhoud[index].startswith('set interfaces lo0 unit 0 family inet address')
                index+=1
            if found:
                index -=1
                ip_address = inhoud[index].split(' ')[8].split('/')[0]
                #print ('Juniper ' + ip_address)
                loopbacklijst[ip_address] = filename
            else:
                log("geen loopback interface gevonden in " + filename)
        config.close()
    log('aantal bestanden in alle_PE folder: '+str(len(loopbacklijst)))
    chdir('..')
    return loopbacklijst

    
def find_interfaces(inhoud, ifname):
    index = 0
    length = len(inhoud)
    while index < length:
        if inhoud[index].startswith("interface "+ ifname):
            return index
        index +=1
    return 0

def analyse(bestand_lijst, bridge_nr):
    neighbor_list=[]
    bandbreedte=""
    cos=""
    mtu = ""
    vpls_id=""
    vlan_desc=""
    if ('interface Vlan'+bridge_nr) in bestand_lijst:
        vfi_regel_nr=bestand_lijst.index('interface Vlan'+bridge_nr)
        #print('bijbehorende vlan interface gevonden '+bridge_nr)
        x_connect_nr=0
        for x in range(vfi_regel_nr, len(bestand_lijst)):
        #Moet tot volgende uitroepteken zijn
            if bestand_lijst[x].startswith('!'):
                break
            if bestand_lijst[x].startswith(' xconnect'):
                if bestand_lijst[x].startswith(' xconnect vfi'):
                    woorden=bestand_lijst[x].split(' ')
                    x_connect_nr=woorden[3]
                    if ('l2 vfi '+x_connect_nr+' manual ') in bestand_lijst:
                        print ('vfi nr '+x_connect_nr)
                        neighbor_regel_nr=bestand_lijst.index('l2 vfi '+x_connect_nr+' manual ')
                        #Zoek regels eronder na voor neighbor, totdat je een ! tegenkomt
                        while bestand_lijst[neighbor_regel_nr] != '!':
                            if bestand_lijst[neighbor_regel_nr].startswith(' vpn id'):
                                # we hebben het vpls-id eigenlijk al
                                woorden=bestand_lijst[neighbor_regel_nr].split(' ')
                                vpls_id= woorden[3]
                            elif bestand_lijst[neighbor_regel_nr].startswith(' neighbor'):
                                woorden=bestand_lijst[neighbor_regel_nr].split(' ')
                                neighbor_list.append(woorden[2])
                            neighbor_regel_nr+=1
                else:
                    print(" directe xconnect")
                    woorden=bestand_lijst[x].split(' ')
                    neighbor_list.append(woorden[2])
                    vpls_id=woorden[3]
                #print('neighbors:')
                #print (neighbor_list)
            
            elif bestand_lijst[x].startswith(' description'):
                vlan_desc = bestand_lijst[x].split(' description',1)[1]
            elif bestand_lijst[x].startswith(' service-policy'):
                regel_list=bestand_lijst[x].split(' ')
                service_policy= regel_list[3]
                if service_policy.strip().endswith('ium') or service_policy.strip().endswith('sic') or service_policy.strip().endswith('ced'):
                    if '-' in service_policy:
                        bandbreedte = service_policy.split('-')[0]
                        cos = service_policy.split('-')[1]
                    else:
                        cos = service_policy
                else:
                    bandbreedte = service_policy
            elif bestand_lijst[x].startswith(' ip address'):
                # toevoegen in volgende release, automatisch omschrijven
                print(" IP adres gevonden")
                log('IP adres voor vlan '+ bridge_nr +' op interface: '+ s_interface)
    else:
        print('geen bijbehorende VLAN gevonden')
        fout.write("service instance "+bridge_nr+ " op interface " + s_interface + " is fout; geen bijbehorende VLAN gevonden\n")
        return neighbor_list,vpls_id, vlan_desc, cos, bandbreedte, mtu
    # let op! mtu moet nog worden uitgezocht!!
    #print(neighbor_list,vpls_id, vlan_desc, cos, bandbreedte, mtu)
    return neighbor_list,vpls_id, vlan_desc, cos, bandbreedte, mtu
        
def change_remote(loopback, vpn_id, oud_ip, nieuw_ip):
    # zoek bestand met loopback adres
    log('change_remote ('+loopback + " "+vpn_id + " van "+ oud_ip+" naar "+nieuw_ip+")")
    print('change_remote ('+loopback + " "+vpn_id + " van "+ oud_ip+" naar "+nieuw_ip+")")
    mypath = "alle_PE"
    chdir(mypath)
    if loopback in loopbacklijst:
        config = open(loopbacklijst[loopback])
        log('remote file is '+loopbacklijst[loopback])
        inhoud = config.read().split('\n')
        config.close()
    else:
        log('geen bestand met loopback ' + loopback + ' gevonden')
        chdir('..')
        return
    #bepaal eerst of Cisco of Juniper
    if ('boot-start-marker') in inhoud:
        is_cisco = True
        is_juniper = False
    else:
        is_cisco = False
        is_juniper = True
     # open out-file ( met loopback; toevoegen, niet overschrijven)
    chdir('..')
    if is_juniper:
        out_filenaam="J_change_"+loopback+"_"+loopbacklijst[loopback]+".txt"
    else:
        out_filenaam="C_change_"+loopback+"_"+loopbacklijst[loopback]+".txt"
    out_file = open(out_filenaam,'a')
           
    if is_cisco:
        # Cisco: verschillende voor
        #xconnect
        #vlan
        #l2vfi
        term = " xconnect "+ oud_ip+ " " + vpn_id + " encapsulation mpls "
        # inderdaad, met een spatie aan het eind
        print ("zoek " + term)
        if (term) in inhoud:
            regel = inhoud.index(term)
            startregel = regel
            gevonden = False
            while not gevonden:
                startregel-=1
                #print("zoek")
                #zoek dan naar de regel die met interface Vlan of met service instance begint
                gevonden = inhoud[startregel].startswith("interface Vlan") 
            if gevonden:
                out_file.write(inhoud[startregel]+"\n")
                out_file.write("no xconnect\n")
                out_file.write("xconnect " + nieuw_ip + " " + vpn_id+ " encapsulation mpls\n")
                out_file.write("!\n")
                #print(inhoud[startregel])
                #print("no xconnect (voor "+inhoud[regel])
                #print("xconnect " + nieuw_ip + " " + vpn_id+ " encapsulation mpls")

        else:
            term = "  xconnect "+ oud_ip+ " " + vpn_id + " encapsulation mpls"
            # dit is een xconnect in een service instance, dus 2 spaties aan het begin
            # of een xconnect op een par, stom genoeg ook met 2 spaties
            print ("zoek twee spaties " + term)
            if (term) in inhoud:
                regel = inhoud.index(term)
                siregel = regel
                gevonden = False
                while not gevonden:
                    siregel-=1
                    #print("zoek")
                    #zoek dan naar de regel die met service instance begint
                    # (Cisco 7600) of een interface Vlan (par)
                    gevonden = inhoud[siregel].startswith(" service instance") or inhoud[siregel].startswith("interface Vlan")
                if gevonden and inhoud[siregel].startswith(" service instance"):
                    # hier moet ook nog de bijbehorende interface gevonden worden
                    ifregel = siregel
                    if_gevonden = False
                    while not if_gevonden:
                        ifregel -=1
                        if_gevonden = inhoud[ifregel].startswith('interface')
                    if if_gevonden:
                        out_file.write(inhoud[ifregel]+'\n')
                        out_file.write(inhoud[siregel]+"\n")
                        out_file.write("no xconnect\n")
                        out_file.write("xconnect " + nieuw_ip + " " + vpn_id+ " encapsulation mpls\n")
                        out_file.write("exit\nexit\nexit\n")
                        #print(inhoud[ifregel])
                        #print(inhoud[siregel])
                        #print("no xconnect (voor "+inhoud[regel])
                        #print("xconnect " + nieuw_ip + " " + vpn_id+ " encapsulation mpls")
                elif gevonden:
                    out_file.write(inhoud[siregel]+"\n")
                    out_file.write("no xconnect\n")
                    out_file.write("xconnect " + nieuw_ip + " " + vpn_id+ " encapsulation mpls\n")
                    out_file.write("!\n")
                    #print("dit was een par " + inhoud[siregel])
                    #print("no "+inhoud[regel])
                    #print("xconnect " + nieuw_ip + " " + vpn_id+ " encapsulation mpls")
        
            else:
                # bv. l2 vfi 63345 manual
                term = "l2 vfi " + vpn_id + " manual "
                # ook hier met opzet een spatie aan het eind
                print ("zoek " + term)
                if term in inhoud:
                    regel = inhoud.index(term)
                    # zoek dan de regel die met neighbor + originele IP adres begint
                    startregel = regel
                    gevonden = False
                    while (not gevonden) and startregel < len(inhoud)-1:
                        startregel+=1
                        #print("zoek" + str(startregel))
                        gevonden = inhoud[startregel].startswith(" neighbor "+ oud_ip)
                    if gevonden:
                        out_file.write(inhoud[regel]+"\n")
                        out_file.write("no "+inhoud[startregel]+"\n")
                        out_file.write(" neighbor " + nieuw_ip + " encapsulation mpls\n")
                        out_file.write("exit\n")
                        #print(inhoud[regel])
                        #print("no "+inhoud[startregel])
                        #print(" neighbor " + nieuw_ip + " encapsulation mpls")
                    if startregel == len(inhoud)-1 and not gevonden:
                        fout.write("geen neighbor gevonden voor "+ loopback + " "+vpn_id + "\n" )
                    
                else:
                    term = " xconnect "+ oud_ip+ " " + vpn_id + " encapsulation mpls"
                    # ja inderdaad, dezelfde zonder spatie komt voor bij Cisco
                    print ("zoek " + term +" zonder spatie!")
                    if (term) in inhoud:
                        regel = inhoud.index(term)
                        startregel = regel
                        gevonden = False
                        while not gevonden:
                            startregel-=1
                            #print("zoek")
                            #zoek dan naar de regel die met interface Vlan begint
                            gevonden = inhoud[startregel].startswith("interface Vlan") 
                        if gevonden:
                            out_file.write(inhoud[startregel]+"\n")
                            out_file.write("no xconnect\n")
                            out_file.write("xconnect " + nieuw_ip + " " + vpn_id+ " encapsulation mpls\n")
                            out_file.write("!\n")
                            #print(inhoud[startregel])
                            #print("no xconnect (voor "+inhoud[regel])
                            #print("xconnect " + nieuw_ip + " " + vpn_id+ " encapsulation mpls")
                    else:                    
                        print ("geen service met id " + vpn_id + " gevonden in deze file")
                        fout.write("geen service met id " + vpn_id + " gevonden in " +loopback + " = PE "+ loopbacklijst[loopback] + "\n")
                out_file.close()
                return
    elif is_juniper:
        # code voor Juniper
        # we moeten zoeken naar iets als set routing-instances 10000503 protocols vpls neighbor 10.31.0.11
        term = 'set routing-instances '+ vpn_id + ' protocols vpls neighbor '+ oud_ip
        if term in inhoud:
            regel = inhoud.index(term)
            #print('gevonden ', term)
            out_file.write('delete routing-instances '+ vpn_id + ' protocols vpls neighbor '+ oud_ip + '\n')
            out_file.write('set routing-instances '+ vpn_id + ' protocols vpls neighbor '+ nieuw_ip+ '\n')
            #print ('delete routing-instances '+ vpn_id + ' protocols vpls neighbor '+ oud_ip)
            #print('set routing-instances '+ vpn_id + ' protocols vpls neighbor '+ nieuw_ip)
        # of we moeten zoeken naar iets als set protocols l2circuit neighbor 10.31.0.5 interface ge-0/0/2.0 virtual-circuit-id 10000099
        else:
            start_term = "set protocols l2circuit neighbor " + oud_ip + " interface"
            end_term = " virtual-circuit-id " + vpn_id
            for i in inhoud:
                if i.startswith(start_term) and i.endswith(end_term):
                    temp_int = i.split("interface")[1].split(" ")[1]
                    #print("l2circuit gevonden!  "+ temp_int)
                    out_file.write("delete protocols l2circuit neighbor " + oud_ip + " interface " + temp_int + " " + end_term + "\n")
                    out_file.write("delete protocols l2circuit neighbor " + oud_ip + " interface " + temp_int + " no-control-word\n")                    
                    out_file.write("set protocols l2circuit neighbor " + nieuw_ip + " interface " + temp_int + " " + end_term + "\n")
                    out_file.write("set protocols l2circuit neighbor " + nieuw_ip + " interface " + temp_int + " no-control-word\n")
                    break
    out_file.close()



    
def classify_translate(inhoud, regel, s_interface, t_interface, t_ip, t_type):
    # de config van s_interface begint op <regel>
    # we kunnen doorzoeken totdat we de volgende regel beginnend met interface tegenkomen, of het einde van de config
    log("translate van interface " + s_interface)
    # eerst alle parameters maar even leeg maken
    bandbreedte=""
    description = ""
    vlan_list = {}
    neighbor_list = {}
    vpls_id = ""    
    while (regel < len(inhoud) and not(inhoud[regel].startswith("interface"))):
        if(inhoud[regel].startswith(" description")):
            description = inhoud[regel].split('description')[1]
            #print(description)
        if(inhoud[regel].startswith(" switchport trunk allowed vlan")):
            heeft_geldige_vlans = False
            #vlans uitpluizen
            vlans = inhoud[regel].split(' ')[5]
            # als de lijst van vlans te groot wordt, maakt Cisco een tweede / derde etc regel die begint
            # met switchport trunk allowed vlan add. Dan moet je het volgende veld nemen voor de vlans!
            if vlans == "add":
                vlans = inhoud[regel].split(' ')[6]
            #print("vlans: "+vlans)
            vlan_list = vlans.split(',')
            #print(vlan_list)

            vlan_list_copy = list(vlan_list)
            for vlan in vlan_list_copy:
                if '-' in vlan:
                    # is dus een range
                    start_vlan = vlan.split("-")[0]
                    end_vlan = vlan.split("-")[1]
                    #print ("start " + start_vlan + " end "+ end_vlan)
                    #expandeer de range naar losse vlans
                    vlan_list.remove(vlan)
                    for i in range(int(start_vlan), int(end_vlan)+1):
                        vlan_list.append(str(i))

            for vlan in vlan_list:
                if vlan != "4000" and vlan != "4001" and vlan != "4020" and vlan != "4021":
                    print("enkeltje "+ vlan)
                    neighbor_list, vpls_id, vlan_desc, cos, bandbreedte, mtu = analyse(inhoud,vlan)
                    
                    if neighbor_list:
                        heeft_geldige_vlans = True
                        for neighbor in neighbor_list:
                            #print(neighbor)
                            change_remote(neighbor, vpls_id, s_ip, t_ip)
                    # nu nog de juniper output genereren
                    if neighbor_list:
                        if vlan_desc:
                            out_file.write('set interfaces '+ t_interface + ' unit ' + vlan + ' description "'+ vlan_desc.strip() + '"\n')
                        out_file.write('set interfaces '+ t_interface + ' unit ' + vlan + ' encapsulation vlan-vpls\n')
                        out_file.write('set interfaces '+ t_interface + ' unit ' + vlan + ' vlan-id ' + vlan + '\n')
                        out_file.write('set interfaces '+ t_interface + ' unit ' + vlan + ' input-vlan-map pop\n')
                        out_file.write('set interfaces '+ t_interface + ' unit ' + vlan + ' output-vlan-map push\n')
                        out_file.write('set interfaces '+ t_interface + ' unit ' + vlan + ' family vpls\n')

                        if(bandbreedte.strip()!=""):
                            out_file.write('set interfaces '+ t_interface + ' unit ' + vlan +' family vpls policer input '+bandbreedte.strip()+'\n')
                        if(t_type == "MX"):
                            out_file.write("set class-of-service interfaces "+t_interface+ " unit "+ vlan + " rewrite-rules ieee-802.1 8021p-rewrite-eurofiber\n")
                        if(t_type == "ACX"):
                            out_file.write("set class-of-service interfaces "+t_interface+ " rewrite-rules ieee-802.1 8021p-rewrite-eurofiber\n")                            
                        if cos!='':
                            out_file.write('set class-of-service interfaces '+t_interface+' unit '+ vlan +' forwarding-class '+cos.capitalize()+'\n')                            

                        ri_pre = 'set routing-instances '+ vpls_id
                        out_file.write(ri_pre + ' instance-type vpls\n')
                        out_file.write(ri_pre + ' interface ' + t_interface + '.' + vlan + '\n')
                        out_file.write(ri_pre + ' protocols vpls encapsulation-type ethernet\n')
                        out_file.write(ri_pre + ' protocols vpls no-tunnel-services\n')
                        out_file.write(ri_pre + ' protocols vpls vpls-id '+ vpls_id + '\n')
                        out_file.write(ri_pre + ' protocols vpls mtu 1600\n')
                        for nb in neighbor_list:
                            out_file.write(ri_pre + ' protocols vpls neighbor ' + nb + '\n')
                elif vlan == "4000" or vlan == "4001" :
                    out_file.write('set interfaces '+ t_interface + ' unit ' + vlan + ' encapsulation vlan-bridge\n')
                    out_file.write('set interfaces '+ t_interface + ' unit ' + vlan + ' vlan-id ' + vlan + '\n')
                    if(t_type == 'MX'):
                        out_file.write('set bridge-domains '+ vlan + ' interface ' + t_interface + '.' + vlan+ '\n')
                    if(t_type == "ACX"):
                        out_file.write('set vlans vlan_'+ vlan + ' interface ' + t_interface + '.' + vlan+ '\n')
                else:
                # nu zijn de vlans dus 4020 en 4021, UNET-NO-CPE
            
                    out_file.write('set interfaces '+ t_interface + ' unit ' + vlan + ' encapsulation vlan-vpls\n')
                    out_file.write('set interfaces '+ t_interface + ' unit ' + vlan + ' vlan-id ' + vlan + '\n')
                    if(t_type == "ACX"):
                        out_file.write('set interface '+ t_interface + ' unit ' + vlan + ' input-vlan-map pop\n')
                        out_file.write('set interface '+ t_interface + ' unit ' + vlan + ' output-vlan-map push\n')
                        out_file.write('set interface '+ t_interface + ' unit ' + vlan + ' family vpls\n')
                    mgmt_vpls=""
                    if vlan == "4020":
                        mgmt_vpls = "64355"
                    if vlan == "4021":
                        mgmt_vpls = "64538"
                    out_file.write('set routing-instances ' + mgmt_vpls + ' interface ' + t_interface + '.' + vlan+ '\n')

            if heeft_geldige_vlans:
                out_file.write('set interfaces '+ t_interface + ' description "'+ description.strip() + '"\n')
                out_file.write('set interfaces '+ t_interface + ' flexible-vlan-tagging\n')
                out_file.write('set interfaces '+ t_interface + ' speed auto\n')
                out_file.write('set interfaces '+ t_interface + ' mtu 1622\n')
                #moet mtu worden overgenomen van de interface of moet die op 1622?
                out_file.write('set interfaces '+ t_interface + ' encapsulation flexible-ethernet-services\n')
                if(t_type == 'MX'):
                    out_file.write('set interfaces '+ t_interface + ' gigether-options auto-negotiation\n')
                if(t_type == 'ACX'):
                    out_file.write('set interfaces '+ t_interface + ' ether-options auto-negotiation\n')
            else:
                log("interface " + s_interface + " heeft geen VLANs die dit script snapt - handmatige check")
                fout.write("interface " + s_interface + " heeft geen VLANs die dit script snapt - handmatige check\n")
        elif(inhoud[regel].startswith(" service instance")):
            print("service instance")
            # kopie van de NNI scripts
            
            gevonden = False
            service_instance=''
            description=''
            vlan_id=''
            neighbor_list=[]
            vpls_id=''
            cos=''
            bandbreedte=''
            regel_list=''
            regel_list= inhoud[regel].split(' ')
            service_instance= regel_list[3]
            regel+=1
            while inhoud[regel] != "!":
                if inhoud[regel].startswith('  encapsulation'):
                    regel_list=inhoud[regel].split(' ')
                    vlan_id =regel_list[4]
                elif inhoud[regel].startswith('  service-policy'):
                    regel_list=inhoud[regel].split(' ')
                    service_policy= regel_list[4]
                    if service_policy.strip().endswith('ium') or service_policy.strip().endswith('sic') or service_policy.strip().endswith('ced'):
                        bandbreedte = service_policy.split('-')[0]
                        cos = service_policy.split('-')[1]
                    else:
                        bandbreedte = service_policy
                elif inhoud[regel].startswith('  xconnect'):
                    gevonden = True
                    regel_list=inhoud[regel].split(' ')
                    neighbor_list=[]
                    neighbor_list.append(regel_list[3])
                    vpls_id = regel_list[4]
                    print("direct xconnect vpls-id " + vpls_id + " neighbor " + neighbor_list[0])

                      
                elif inhoud[regel].startswith('  bridge-domain'):
                    print('bridge domain gevonden ' + inhoud[regel])
                    gevonden = True
                    woorden=inhoud[regel].split(' ')
                    bridge_nr= woorden[3]
                    neighbor_list, vpls_id, vlan_desc, cos, bandbreedte, mtu = analyse(inhoud,bridge_nr)
                regel+=1
        #elif inhoud[regel].startswith('  description'):
            #description=inhoud[regel].split('  description ',1)
            #description = description [1]


            # tot hier kopie van NNI script
            # en nog de Juniper configuratie maken!
            #out_file.write('set interfaces '+ t_interface + ' description'+ description + '\n')
            #out_file.write('set interfaces '+ t_interface + ' flexible-vlan-tagging\n')
            #out_file.write('set interfaces '+ t_interface + ' speed auto\n')
            #out_file.write('set interfaces '+ t_interface + ' mtu 1622\n')
            #out_file.write('set interfaces '+ t_interface + ' encapsulation flexible-ethernet-services\n')
            #out_file.write('set interfaces '+ t_interface + ' gigether-options auto-negotiation\n')
                
        elif (inhoud[regel].startswith(" switchport access")):
            print("access vlan")
            vlan = inhoud[regel].split(' ')[4]
            print(vlan)
            out_file.write('set interfaces '+ t_interface + ' description "'+ description.strip() + '"\n')
            out_file.write('set interfaces '+ t_interface + ' speed auto\n')
            out_file.write('set interfaces '+ t_interface + ' mtu 1614\n')
            out_file.write('set interfaces '+ t_interface + ' encapsulation ethernet-vpls\n')
            if(t_type == "MX"):
                out_file.write('set interfaces '+ t_interface + ' gigether-options auto-negotiation\n')
                out_file.write('set interfaces '+ t_interface + ' unit 0 family vpls\n')
            if(t_type == "ACX"):
                out_file.write('set interfaces '+ t_interface + ' ether-options auto-negotiation\n')
            out_file.write('set interfaces '+ t_interface + ' unit 0 family vpls\n')
            
            neighbor_list, vpls_id, vlan_desc, cos, bandbreedte, mtu = analyse(inhoud,vlan)
            #print(neighbor_list)
            #print(vpls_id)
            #zoek hier verder naar de bandbreedte config van de interface
            regel+=1
            while(regel < len(inhoud)) and inhoud[regel] != "!":
                if inhoud[regel].startswith(" service-policy input "):
                    if "-" in inhoud[regel].split("input")[1]:
                        bandbreedte = inhoud[regel].split("input")[1].split("-")[0].strip()
                        cos = inhoud[regel].split("input")[1].split("-")[1]
                        print("bandbreedte " + bandbreedte)
                        break
                    else:
                        bandbreedte = inhoud[regel].split("input")[1].strip()
                        cos=""
                        break
                regel+=1
            
            if neighbor_list:
                if(vlan_desc):
                    out_file.write('set interfaces '+ t_interface + ' unit 0'+ ' description "'+ vlan_desc.strip() + '"\n')

                if(bandbreedte.strip()!=""):
                    out_file.write('set interfaces '+ t_interface + ' unit 0'+' family vpls policer input '+bandbreedte.strip()+'\n')
                if(t_type == "MX"):
                    out_file.write("set class-of-service interfaces "+ t_interface + " unit 0 rewrite-rules ieee-802.1 8021p-rewrite-eurofiber\n")
                if(t_type == "ACX"):
                    out_file.write("set class-of-service interfaces "+ t_interface + " rewrite-rules ieee-802.1 8021p-rewrite-eurofiber\n")                
                if cos!='':
                    out_file.write('set class-of-service interfaces '+t_interface+' unit 0' + ' forwarding-class '+cos.capitalize()+'\n')                            

                ri_pre = 'set routing-instances '+ vpls_id
                out_file.write(ri_pre + ' instance-type vpls\n')
                out_file.write(ri_pre + ' interface ' + t_interface + '.0' + '\n')
                out_file.write(ri_pre + ' protocols vpls encapsulation-type ethernet\n')
                out_file.write(ri_pre + ' protocols vpls no-tunnel-services\n')
                out_file.write(ri_pre + ' protocols vpls vpls-id '+ vpls_id + '\n')
                out_file.write(ri_pre + ' protocols vpls mtu 1600\n')
                for nb in neighbor_list:
                    out_file.write(ri_pre + ' protocols vpls neighbor ' + nb + '\n') 
                    change_remote(nb, vpls_id, s_ip, t_ip)
        elif(inhoud[regel].startswith(" xconnect")):
            print("xconnect")
            bandbreedte=""
            woorden=inhoud[regel].split(' ')
            neighbor = woorden[2]
            vpls_id = woorden[3]
            out_file.write("set protocols l2circuit neighbor "+ neighbor + " interface "+ t_interface + ".0 virtual-circuit-id "+ vpls_id + "\n")
            out_file.write("set protocols l2circuit neighbor "+ neighbor + " interface "+ t_interface + ".0 no-control-word\n")
            if(t_type == "MX"):
                out_file.write("set class-of-service interfaces "+ t_interface + " unit 0 rewrite-rules ieee-802.1 8021p-rewrite-eurofiber\n")
            if(t_type == "ACX"):
                out_file.write("set class-of-service interfaces "+ t_interface + " rewrite-rules ieee-802.1 8021p-rewrite-eurofiber\n")
            out_file.write("set interfaces "+ t_interface + ' description "'+ description.strip()+'"\n')
            out_file.write("set interfaces "+ t_interface + " mtu 1614\n")
            out_file.write("set interfaces "+ t_interface + " encapsulation ethernet-ccc\n")
            #bandbreedte opzoeken in Cisco config, kan iets zijn als 200Mbps-Premium of iets als Premium
            regel+=1
            while(regel < len(inhoud)) and inhoud[regel] != "!":
                if inhoud[regel].startswith(" service-policy input "):
                    if "-" in inhoud[regel].split("input")[1]:
                        bandbreedte = inhoud[regel].split("input")[1].split("-")[0]
                        cos = inhoud[regel].split("input")[1].split("-")[1]
                        break
                    else:
                        bandbreedte = inhoud[regel].split("input")[1]
                        cos=""
                        break
                regel+=1            
            if bandbreedte:
                if not bandbreedte[:3].isdigit():
                    fout.write("de bandbreedte van interface " + s_interface + " begint niet met een getal, handmatige actie nodig\n")                
                else:
                    if(t_type == "MX"):
                        out_file.write("set interfaces "+ t_interface + " unit 0 family ccc policer input "+ bandbreedte.strip() + "\n")
                    if(t_type == "ACX"):
                        # herschrijf de Mbps in Mb!! en gebruik filter ipv policer
                        out_file.write("set interfaces "+ t_interface + " unit 0 family ccc filter input "+ bandbreedte.strip()[:-2] + "\n")
                    if cos:
                        out_file.write('set class-of-service interfaces '+t_interface+' unit 0' + ' forwarding-class '+cos.capitalize()+'\n')                            

            change_remote(neighbor, vpls_id, s_ip, t_ip)
        
        regel+=1



#main
logfile = open('log.txt','w')
fout=open('fout.txt','w')
out_file = open('juniper_config.txt','w')

#open mapping file en zoek de pe naam op
try:
    mapping_file = open('mapping.txt')
    mapping = mapping_file.read().split('\n')
    mapping_file.close()
except:
    print('trouble opening mapping file')
    log('trouble opening mapping file')
    sys.exit()

pe_naam = mapping[0]

# maak dan de loopbacklijst van alle PEs in netwerk
loopbacklijst = create_loopbacks()

# en zoek het loopback IP adres van de te migreren PE op
s_ip=""
for i in loopbacklijst:
    if loopbacklijst[i].lower()== pe_naam.lower():
        s_ip = i
        #print(i)
        break
if s_ip=="":
    fout.write("source PE "+ pe_naam + " niet gevonden in de loopbacklijst\n")
    print("source PE "+ pe_naam + " niet gevonden in de loopbacklijst\n")
# open config file van de PE
try:
    chdir("alle_PE")
    config_file = open(pe_naam)
    config = config_file.read().split('\n')
    config_file.close()
    chdir("..")
except:
    print('trouble opening pe config file '+pe_naam)
    log('trouble opening pe config file '+pe_naam)
    sys.exit()

# loop alle interfaces na die gemigreerd moeten worden
for i in range(1,len(mapping)):
    if mapping[i] != "":
        s_interface = mapping[i].split(" ")[0]
        t_interface = mapping[i].split(" ")[1]
        t_ip = mapping[i].split(" ")[2]
        t_type = mapping[i].split(" ")[3]
        # vind de regel in de configuratie waar de interface begint
        regel = find_interfaces(config, s_interface)
        print(str(regel) + "   " + mapping[i])
        
        # zoek daarna de configuratie uit en vertaal in Juniper taal
        classify_translate(config, regel+1, s_interface, t_interface, t_ip, t_type)
        # de regel+1 is omdat we op de volgende regel moeten beginnen
logfile.close()
fout.close()
out_file.close()

