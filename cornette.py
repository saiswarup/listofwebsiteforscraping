from email import header
from json.tool import main
import os
import xlrd
import requests
import dateparser
import html5lib
from bs4 import BeautifulSoup
import csv
import sys
import re
import pandas as pd
from datetime import date, datetime
from cryptography.fernet import Fernet
from csv import DictWriter
from dateutil import parser
import json
#import pprintk
from quantulum3 import parser as qtlum

urllist=[]

def getitemurls(mainurl,pageno):
    AuctionInfo={}
    # checkcat=re.findall('https://(.*).ha.com', mainurl) 
    # currenturl=mainurl
    # getmainpage=mainurl.split("/c/")
    # print(getmainpage)
    
#         headers={
#     "Host":checkcat[0]+".ha.com",
#     "User-Agent":
#       "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:96.0) Gecko/20100101 Firefox/96.0",

#     "Connection": "keep-alive",
#     "Cookie":
#       "KP_UIDz-ssn=02jQsD8fIro8w5jKY7bi6DC9LjIRLgmabR5aUjq1wT54zZES8DAMqZU59GQ5NyI5ZUz2e0DR5CNGvf6tlO4LZ6XpuIxJQV79gL5AEVBbDfsjOv0GkoEtsWnBmPO5Uw9RCCsx6AUUT5LSsvoPhtQiZndNI91; KP_UIDz=02jQsD8fIro8w5jKY7bi6DC9LjIRLgmabR5aUjq1wT54zZES8DAMqZU59GQ5NyI5ZUz2e0DR5CNGvf6tlO4LZ6XpuIxJQV79gL5AEVBbDfsjOv0GkoEtsWnBmPO5Uw9RCCsx6AUUT5LSsvoPhtQiZndNI91; CNo=TkxzUHpSZzYvT0JXY04wPS5zbmZDdVBmRFJzdCtOeEZZLlFRdFJvcis4TTlBQmp5NDVKY0hpR1E9PQ%3D%3D; OR=418678472; SR=https%3A%2F%2Fmail.google.com%2F; RawSR=https%3A%2F%2Fmail.google.com%2F; OptanonConsent=isGpcEnabled=0&datestamp=Thu+Jan+20+2022+23%3A48%3A37+GMT%2B0530+(India+Standard+Time)&version=6.22.0&isIABGlobal=false&hosts=&landingPath=NotLandingPage&groups=1%3A1%2C2%3A1%2C3%3A1%2C4%3A1&AwaitingReconsent=false&geolocation=IN%3BMH; s_fid=1000C0280CDC2DC8-2782E51E37004D79; s_nr=1642702716034-Repeat; _ga=GA1.2.624529090.1642501612; _gid=GA1.2.703807483.1642501612; _gcl_au=1.1.220912212.1642501612; s_vi=[CS]v1|30F34AF6A9E67C89-40000DE65EA8D346[CE]; OptanonAlertBoxClosed=2022-01-20T18:18:36.822Z; cto_bundle=o7fIM19zNFQyQ0pkZjI5ZUFaTjlJb2NLSFJYb2Y5Nm54ZGlqZXYlMkJSR2hGWGdtMVhhR0dXd2FKJTJCMTJTNVBDY3ZUWnEzelRsR0gxSWZreGF0TzVQWDdVTlJCWE5IJTJCYmlpV0EwVncxNDUwSDQ1Z1JsMnhxdXVYOTZwSGJMNDlqb1VYWnZBVzZhZXl1byUyRlhRJTJCaFBadXJ6cm5sTkhBJTNEJTNE; anon-up=a%3A11%3A%7Bs%3A9%3A%22viewAdult%22%3Bi%3A0%3Bs%3A3%3A%22rpp%22%3Bi%3A100%3Bs%3A4%3A%22erpp%22%3Bs%3A2%3A%2224%22%3Bs%3A4%3A%22vrpp%22%3Bi%3A25%3Bs%3A6%3A%22comics%22%3Ba%3A2%3A%7Bs%3A10%3A%22searchView%22%3Bs%3A7%3A%22gallery%22%3Bs%3A14%3A%22bidBuySearchIn%22%3Bs%3A9%3A%22SI_Titles%22%3B%7Ds%3A10%3A%22bidBuySort%22%3Bs%3A0%3A%22%22%3Bs%3A11%3A%22archiveSort%22%3Bs%3A0%3A%22%22%3Bs%3A17%3A%22hideWantlistModal%22%3Bi%3A0%3Bs%3A18%3A%22haliveCurrencyCode%22%3Bs%3A3%3A%22USD%22%3Bs%3A17%3A%22haliveHideYouTube%22%3Bs%3A1%3A%220%22%3Bs%3A15%3A%22disabledDialogs%22%3Bs%3A1%3A%22%7C%22%3B%7D; SessionID=13qi54l5a6g3itjbumr5rl11q3; test=123; LastSessionHit=1642702648; TS01bf530f=01b44f9845902442447d06147695234751ab5989b10bd610896a408d70870e7980759e2a46402c6f13747173a8523a4effd4266188; TS01bb2cd9=01b44f98459a7d8764e5805feac59a09363c9f17f49da6005ad2b02bc22630470c2b4d2bac195c686da19154904bbc66b1e885ea1f; js=1; s_custnum=0; s_cc=true; s_sq=%5B%5BB%5D%5D; _gat=1",
#     "Upgrade-Insecure-Requests": "1",
#     "Sec-Fetch-Dest": "document",
#     "Sec-Fetch-Mode": "navigate",
#     "Sec-Fetch-Site": "none",
#     "Sec-Fetch-User": "?1",
#   }

        #r=requests.get(currenturl, headers=headers,allow_redirects=False)
    if mainurl.split('catalogue/').__len__() > 1:
        acno=mainurl.split('catalogue/')[1]
    else:
        acno = []
    r=requests.get(mainurl,allow_redirects=False)
    soup=BeautifulSoup(r.text,'html.parser')
    #print(soup)
    
    mydivs = soup.find_all("div",{"class":"product-desc"})
    otdetails=soup.find("div",{"class":"entete_cata col-md-7 Vente116114 Etude1124 Etude2288"})
    acname=otdetails.select(".nom_vente")
    acname=acname[0].text.strip()
    acdate=otdetails.select(".date_vente")
    acdate=acdate[0].text.strip()
    
    acloc=otdetails.select(".lieu_vente")
    acloc=acloc[0].text.strip()
    
    acdate=str(dateparser.parse(acdate).date())
    acdate=parser.parse(acdate)
    acdate=acdate.strftime("%d-%b-%y")
    print(acdate)
    print(acloc)
    for x in mydivs:
        u = x.find("a")
        link='https://auction-cornettedesaintcyr-fr.translate.goog'+u['href']+'_x_tr_sl=auto&_x_tr_tl=en&_x_tr_hl=en&_x_tr_pto=wapp'
        urllist.append(link)
        #print(u['href'])

        
    #print(mydivs)
    
    # jsonresp=r.json()
    # #print(jsonresp)
    # r2=requests.get("https://www.woolleyandwallis.co.uk/departments/paintings/pw010322/?p=1&s=40&v=list#lot-1",allow_redirects=False)

    # obj=jsonresp['Results']
    
    # soup = BeautifulSoup(r2.text,'html.parser')
    # mydivs = soup.find("div",{"class":"image-title-inner"})
    # listpaint=mydivs.find_all("h1")
    # acdate=mydivs.find_all("strong")
    # print(listpaint[0].text)
    # acname=acdate[0].text.split('.')[0]
    # x2=acdate[0].text.split('.')[0]
    # x22=parser.parse(x2)
    # x22=x22.strftime("%d-%b-%y")
    # print(x22)
    
    #print(soup)
    #print(soup)
    

    # mydivs = soup.find("div", {"class": "c-lot-index__lots"})
    # listpaint=mydivs.find_all("div", {"class": "c-lot-index-lot js-market-lot-index-lot js-push-lot-index-lot"})
    # for v in listpaint:
    #     link=v.find("a", {"class": "c-lot-index-lot__link ga-lot-index-lot"})
    #     #print('\n')
    #     #print(link['href'])
    #     urllist.append('https://www.bukowskis.com/'+link['href'])
    return acdate,acname,acloc,acno
def getitemdetails(mainurl,csvpath,x22,acname,acloc,acno):
    r=requests.get(mainurl)
    soup=BeautifulSoup(r.text,'html.parser')
    #print(soup)
    AuctionInfo={}
    MainData={}
    MainData["artwork_category"]=''
    #MainData["artcategory"]=''
    MainData["auction_location"]='Brussels'
    MainData["auction_num"]=acno
    MainData["lot_num"]=''
    lotno=soup.select_one('.fiche_lot_num').text
    MainData["lot_num"]=lotno
    MainData["auction_house_name"]="Cornette DeSaintCyr"
    MainData["auction_name"]=acname
    MainData["auction_end_date"]=""
    MainData["sublot_num"]=""
    MainData["auction_start_date"]=x22
    artistname=soup.select_one('#page-title')
    artistname=artistname.find('h1')
    artistname=artistname.text
    MainData["lot_origin_url"]=mainurl
    MainData["artist_nationality"]=''
    MainData["artist_birth"]=''
    MainData["artist_death"]=''
    MainData["price_estimate_min"]=""
    MainData["price_estimate_max"]=''
    MainData["artwork_year_identifier"]=''
    MainData["artwork_provenance"]=''
    MainData["artwork_literature"]=''
    MainData["artwork_exhibited"]=''
    if(artistname.find('(')!=-1 ):
        MainData["artist_name"]=artistname.split('(')[0]
        datecontent=artistname[artistname.find("(")+1:artistname.find(")")]
        datecontent=datecontent.split('-')
        # MainData["artwork_name"]=desc[1].replace('<p>','').replace('</p>','')
        if(len(datecontent)>1):
            MainData["artist_birth"]=datecontent[0]
            MainData["artist_death"]=datecontent[1]
        else:
            MainData["artist_birth"]=datecontent[0]
    
    estimaterange=soup.select_one('.estimAff4')
    try:
        estimaterange=estimaterange.text.replace('EUR','').strip()
        estimaterange=estimaterange.split('-')
        if(len(estimaterange)>1):
            MainData["price_estimate_min"]=estimaterange[0]
            MainData["price_estimate_max"]=estimaterange[1]
        else:
            MainData["price_estimate_min"]=estimaterange[0]
    except:
        pass
    
    hammerprice=soup.select_one('.fiche_lot_resultat')
    if(hammerprice is None):
        print("No hammerprice")
        MainData["price_sold"]=''
        MainData["price_kind"]='estimate'
    else:
        MainData["price_sold"]=hammerprice.text.replace('Résultat :','').replace('EUR','').strip().encode('ascii', 'ignore').decode("utf-8")
        MainData["price_kind"]='price realised'
    imgmain=soup.select_one('noscript')
    MainData["artwork_images1"]=''
    try:
        imgmain=imgmain.select_one('img')
        imgmain=imgmain['src'].replace('phare','fullHD')
        MainData["artwork_images1"]=imgmain
    except:
        pass
    desc=soup.select_one('.fiche_lot_description')
    desclist=desc.text.strip().split('\n')
    title=desclist[0]
    artworkyear=title.split(',')
    MainData['artwork_start_year']=''
    s=title.split(' ')
    name=''
    for v in s:
        try:
            if(v[1].islower()):
                break
        except:
            pass
        name=name+''.join([c for c in v if c.isupper()])+' '
        
    MainData['artwork_name']=name
    if(len(artworkyear)>1):
        MainData['artwork_start_year']=artworkyear[1]
    print(desclist)
    df = pd.read_excel('/root/artwork/deploydirnew/docs/fineart_materials.xls')
    mylist1 = df['material_name_fr'].tolist()    
    
    for i in range(len(desclist)):
        
        if(desclist[i].find('mm')!=-1 or desclist[i].find('cm')!=-1 or desclist[i].find('inches')!=-1):
                
                try:
                    quants = qtlum.parse(desclist[i].split('-')[1])
                    sizenote=str(quants[0].value)+'x'+str(quants[1].value)+quants[1].unit.name
                    MainData["auction_measureunit"]='cm' if quants[1].unit.name=='centimetre' else 'inches' if quants[1].unit.name=='inch' else 'mm' if quants[1].unit.name=='millimetre' else 'unknown'
                    MainData["artwork_measurements_height"]=quants[0].value
                    MainData["artwork_measurements_width"]=quants[1].value
                    MainData["artwork_size_notes"]=sizenote
                except:
                    pass
        if(desclist[i].lower().find('signée')!=-1):
            pattern = r'[0-9]'

            MainData["artwork_markings"]=desclist[i].replace('<p>','').replace('</p>','').strip().encode('ascii', 'ignore').decode("utf-8").split('-')[0].replace('cm','')
            new_string = re.sub(pattern, '', MainData["artwork_markings"])
            MainData["artwork_markings"]=new_string
        if(desclist[i].lower().find('provenance')!=-1):
            MainData["artwork_provenance"]=desclist[i+1:len(desclist)-1]
            listToStr = ' '.join([str(elem) for elem in MainData["artwork_provenance"]])
            listToStr=listToStr.replace('<p>','').replace('</p>','')
            MainData["artwork_provenance"]=listToStr.strip().replace('\n','')
        for t in range(len(mylist1)):
            if(desclist[i].lower().find(desclist[i].replace("'","").lower())!=-1):
                MainData["artwork_category"]=df['material_category'][t]
                MainData["artwork_materials"] = desclist[i].strip()

    listToStr = ' '.join([str(elem) for elem in desclist])    
    #desc=obj['FullDescription']
    MainData['artwork_description']='<strong><br>Description:</strong><br>'+listToStr.strip()   
    MainData["artwork_edition"]=''
    MainData["artwork_condition_in"]=''
    
    #MainData["auction_measureunit"]=''
    #MainData["estimaterange"]=''
    #MainData["artwork_images1"]=''
    MainData["artwork_images2"]=''
    MainData["artwork_images3"]=''
    MainData["artwork_images4"]=''
    MainData["artwork_images5"]=''
    MainData["artwork_images6"]=''
    MainData["image1_name"]=''
    MainData["image2_name"]=''
    MainData["image3_name"]=''
    MainData["image4_name"]=''
    
    #csvpath=csvpath+"/"+"Cornette"+"_"+str(MainData["auction_num"])+'.csv'
    keys=["auction_house_name","auction_location","auction_num","auction_start_date","auction_end_date","auction_name","lot_num","sublot_num","price_kind","price_estimate_min","price_estimate_max","price_sold","artist_name","artist_birth","artist_death","artist_nationality","artwork_name","artwork_year_identifier","artwork_start_year","artwork_end_year","artwork_materials","artwork_category","artwork_markings","artwork_edition","artwork_description","artwork_measurements_height","artwork_measurements_width","artwork_measurements_depth","artwork_size_notes","auction_measureunit","artwork_condition_in","artwork_provenance","artwork_exhibited","artwork_literature","artwork_images1","artwork_images2","artwork_images3","artwork_images4","artwork_images5","artwork_images6","image1_name","image2_name","image3_name","image4_name","image5_name","lot_origin_url"]
        
    file_exist=os.path.isfile(csvpath)
    with open(csvpath, 'a',encoding="utf-8", newline='') as output_file:
        keys=["auction_house_name","auction_location","auction_num","auction_start_date","auction_end_date","auction_name","lot_num","sublot_num","price_kind","price_estimate_min","price_estimate_max","price_sold","artist_name","artist_birth","artist_death","artist_nationality","artwork_name","artwork_year_identifier","artwork_start_year","artwork_end_year","artwork_materials","artwork_category","artwork_markings","artwork_edition","artwork_description","artwork_measurements_height","artwork_measurements_width","artwork_measurements_depth","artwork_size_notes","auction_measureunit","artwork_condition_in","artwork_provenance","artwork_exhibited","artwork_literature","artwork_images1","artwork_images2","artwork_images3","artwork_images4","artwork_images5","artwork_images6","image1_name","image2_name","image3_name","image4_name","image5_name","lot_origin_url"]
            #keys = MainData.keys()
        #print(keys)
        # print(type(MainData))
        dictwriter_object = DictWriter(output_file,fieldnames=keys)
        if not file_exist:
            dictwriter_object.writeheader()
            dictwriter_object.writerow(MainData)
            output_file.close()
        else:
            dictwriter_object.writerow(MainData)
            output_file.close()

            #MainData["artwork_year_identifier"]=obj['Title'].split('c.')[1]
   #COMMENTED SECTION START 
    # MainData["price_estimate_min"]=obj['LowerEstimate']
    # MainData["price_estimate_max"]=obj['UpperEstimate']
    # MainData["artwork_year_identifier"]=""
    # MainData["artwork_end_year"]=""
    # if(obj['HammerPrice']==None or obj['HammerPrice']==0.00 or obj['HammerPrice']=='null'):
    #     MainData["price_kind"]='estimate'
    #     MainData["price_sold"]=''
    # else:
    #     MainData["price_kind"]='price realised'
    #     MainData["price_sold"]=obj['HammerPrice']
    # MainData["artwork_markings"]=''


    # MainData["artwork_measurements_height"]=''
    # MainData["artwork_measurements_width"]=''
    # MainData["artwork_measurements_depth"]=''
    # MainData["auction_measureunit"]='cm'
    
    # 
    # desc=obj['FullDescription']
    # MainData['artwork_description']='<strong><br>Description:</strong><br>'+desc
    # MainData["artwork_provenance"]=''
    # MainData["artwork_literature"]=''
    # MainData["artwork_exhibited"]=''
    # desc=desc.split('\n')
    # for i in range(len(desc)):
    #     if(desc[i].lower().find('signed')!=-1):
    #         MainData["artwork_markings"]=desc[i].replace('<p>','').replace('</p>','')
    #     if(desc[i].find('mm')!=-1 or desc[i].find('cm')!=-1 or desc[i].find('inches')!=-1):
    #             quants = qtlum.parse(desc[i])
    #             try:
    #                 sizenote=str(quants[0].value)+'x'+str(quants[1].value)+quants[1].unit.name
    #                 MainData["auction_measureunit"]='cm' if quants[1].unit.name=='centimetre' else 'inches' if quants[1].unit.name=='inches' else 'mm' if quants[1].unit.name=='millimetre' else 'unknown'
    #                 MainData["artwork_measurements_height"]=quants[0].value
    #                 MainData["artwork_measurements_width"]=quants[1].value
    #                 MainData["artwork_size_notes"]=sizenote
    #             except:
    #                 pass
    #     if(desc[i].lower().find('provenance')!=-1):
    #         MainData["artwork_provenance"]=desc[i+1:len(desc)-1]
    #         listToStr = ' '.join([str(elem) for elem in MainData["artwork_provenance"]])
    #         listToStr=listToStr.replace('<p>','').replace('</p>','')
    #         MainData["artwork_provenance"]=listToStr
            

    
   
    # MainData["lot_origin_url"]='https://www.woolleyandwallis.co.uk'+obj['ViewUrl']
    # MainData["artist_nationality"]=''
    # MainData["artist_birth"]=''
    # MainData["artist_death"]=''
    
    
    # if(obj['Title'].find('λ')!=-1 and obj['Title'].find('(')!=-1 ):
    #     MainData["artist_name"]=obj['Title'].replace('λ','').split('(')[0]
    #     datecontent=obj['Title'][obj['Title'].find("(")+1:obj['Title'].find(")")]
    #     datecontent=datecontent.split('-')
    #     MainData["artwork_name"]=desc[1].replace('<p>','').replace('</p>','')
    #     if(len(datecontent)>1):
    #         MainData["artist_birth"]=datecontent[0]
    #         MainData["artist_death"]=datecontent[1]
    #     else:
    #         MainData["artist_birth"]=datecontent[0]
    #         #MainData["artwork_year_identifier"]=obj['Title'].split('c.')[1]



       
    # else:
    #     MainData["artist_name"]=''
    #     MainData["artwork_name"]=obj['Title']
    #     if(obj['Title'].find('c.')!=-1):
    #         MainData["artwork_year_identifier"]=obj['Title'].split('c.')[1]
            
    # MainData["artwork_materials"]=''
    # # print("Lenght Desc")
    # # print(desc[4])
    # #MainData["artwork_size_notes"]=''
    # try:
    #     if desc[2].lower().find('signed')==-1:
    #         MainData["artwork_materials"]=desc[2].replace('<p>','').replace('</p>','')
    #     else:
    #         MainData["artwork_materials"]=desc[3].replace('<p>','').replace('</p>','')
    # except:
    #     pass
    
    # MainData["artwork_edition"]=''
    # MainData["artwork_condition_in"]=''
    # MainData['artwork_condition_in']=obj['ConditionReport']
    # #MainData["auction_measureunit"]=''
    # #MainData["estimaterange"]=''
    # MainData["artwork_images1"]=''
    # MainData["artwork_images2"]=''
    # MainData["artwork_images3"]=''
    # MainData["artwork_images4"]=''
    # MainData["artwork_images5"]=''
    # MainData["artwork_images6"]=''
    # MainData["image1_name"]=''
    # MainData["image2_name"]=''
    # MainData["image3_name"]=''
    # MainData["image4_name"]=''
    # #MainData["imgdescription"]=''
    # r3=requests.get(MainData["lot_origin_url"])
    # soup = BeautifulSoup(r3.text,'html.parser')
    # #print(soup)
    # mydivs = soup.find("ul",{"class":"slider--list"})
    # listpaint=mydivs.find_all("li")
    # p=1
    # for x in listpaint:
    #     img=x.find('img')
    #     print(img['src'])
    #     dd="artwork_images"+str(p)
    #     p+=1
    #     MainData[dd]=img['src']
    # csvpath=csvpath+"/"+"WnW"+"_"+str(MainData["auction_num"])+'.csv'
    # keys=["auction_house_name","auction_location","auction_num","auction_start_date","auction_end_date","auction_name","lot_num","sublot_num","price_kind","price_estimate_min","price_estimate_max","price_sold","artist_name","artist_birth","artist_death","artist_nationality","artwork_name","artwork_year_identifier","artwork_start_year","artwork_end_year","artwork_materials","artwork_category","artwork_markings","artwork_edition","artwork_description","artwork_measurements_height","artwork_measurements_width","artwork_measurements_depth","artwork_size_notes","auction_measureunit","artwork_condition_in","artwork_provenance","artwork_exhibited","artwork_literature","artwork_images1","artwork_images2","artwork_images3","artwork_images4","artwork_images5","artwork_images6","image1_name","image2_name","image3_name","image4_name","image5_name","lot_origin_url"]
        
    # file_exist=os.path.isfile(csvpath)
    # with open(csvpath, 'a',encoding="utf-8", newline='') as output_file:
    #     keys=["auction_house_name","auction_location","auction_num","auction_start_date","auction_end_date","auction_name","lot_num","sublot_num","price_kind","price_estimate_min","price_estimate_max","price_sold","artist_name","artist_birth","artist_death","artist_nationality","artwork_name","artwork_year_identifier","artwork_start_year","artwork_end_year","artwork_materials","artwork_category","artwork_markings","artwork_edition","artwork_description","artwork_measurements_height","artwork_measurements_width","artwork_measurements_depth","artwork_size_notes","auction_measureunit","artwork_condition_in","artwork_provenance","artwork_exhibited","artwork_literature","artwork_images1","artwork_images2","artwork_images3","artwork_images4","artwork_images5","artwork_images6","image1_name","image2_name","image3_name","image4_name","image5_name","lot_origin_url"]
    #         #keys = MainData.keys()
    #     #print(keys)
    #     # print(type(MainData))
    #     dictwriter_object = DictWriter(output_file,fieldnames=keys)
    #     if not file_exist:
    #         dictwriter_object.writeheader()
    #         dictwriter_object.writerow(MainData)
    #         output_file.close()
    #     else:
    #         dictwriter_object.writerow(MainData)
    #         output_file.close()
    #     if(dd=='artwork_images7'):
    #     	break
    #     v=imglinks[uu].find('img')
        
    #     MainData[dd]=''
    #     just=v['src']
    #     MainData[dd]=just
    #     #print(imagelist[uu])
    # for x in listpaint:
    #     print(x)
#COMMENTED SECTION END 
   

    #print(obj)
    print(MainData)
    

        #r=requests.get(currenturl, headers=headers,allow_redirects=False)
    # r=requests.get(mainurl,allow_redirects=False)
    # MainData["lot_origin_url"]=mainurl


    # soup = BeautifulSoup(r.text,'html.parser')
    # lotno=soup.find_all("div", {"class": "c-market-lot-show-header__identifiers"})
    # try:
    #     lotno=lotno[0].text
    #     MainData["lot_num"]=lotno
    # except:
    #     pass
    # try:
    #     auctionname=soup.find_all("a", {"class": "c-market-lot-show-navigation__link c-market-lot-show-navigation__link--auction"})
    #     auctionname=auctionname[0].text
    #     MainData['auction_name']=auctionname
    # except:
    #     pass
    # auctionndate=soup.find("div", {"class": "c-market-lot-sidebar__ending"})

    

    
    # description=soup.find_all("div", {"class": "c-market-lot-show-header__title-container"})
    # print(description)
    # dates=''
    # try:
    #     dates=description[0].select_one(".c-market-lot-show-header__artist-lifetime")
    #     dates=dates.text[dates.text.find("(")+1:dates.text.find(")")]
    #     dates=dates.split(',')
    #     MainData["artist_nationality"]=dates[0]
    #     try:
    #         MainData["artist_birth"]=dates[1].split('-')[0]
    #         MainData["artist_death"]=dates[1].split('-')[1]
    #     except:
    #         pass
    # except:
    #     pass

    # try:
    #     MainData["artist_name"]=description[0].find("h1").text
    # except:
    #     pass
    # location=soup.find_all("div", {"class": "c-market-lot-show-info__placement"})
    # #MainData['auction_location']=location[0].text.replace('Location:','').strip()
    # MainData["auction_location"]="Stockholm"
    # auctiondate=soup.find_all("time", {"class": "c-market-lot-show-bidding-end-date"})
    # x22=parser.parse(auctiondate[0]['datetime'])
    # x22=x22.strftime("%d-%b-%y")
    # MainData["auction_start_date"]=x22
    # estimate=soup.find_all("div", {"class": "c-market-lot-show-estimate__amount"})
    # print(estimate[0].text)
    # MainData["price_estimate_max"]=estimate[0].text.strip().encode('ascii', 'ignore').decode("utf-8").replace('SEK','')
    # currentbid =soup.find_all("div", {"class": "c-market-lot-show-result"})
    # if(currentbid[0].text.find('Contact')==-1):
    #     print(currentbid[0].text)
    #     try:
    #         MainData["price_sold"]=currentbid[0].find("div",{"class":"c-market-lot-show-result__leading-amount c-market-lot-show-result__leading-amount--reserve-met"}).text.strip().encode('ascii', 'ignore').decode("utf-8") 
    #         MainData["price_kind"]="price realised"
    #     except:
    #         MainData["price_kind"]="estimate"
            
    # else:
    #     MainData["price_kind"]="estimate"
    # #c-market-lot-show-info
    # maindesc=soup.find_all("div", {"class": "c-market-lot-show-info"})
    # tesdesc=soup.find_all("p")
    # for j in tesdesc:
    #     aname=re.findall('"([^"]*)"', j.text)
    #     try:
    #         MainData["artwork_name"]=aname[0]
    #     except:
    #         pass
        
    # try:
    #     aname=re.findall('”([^"]*)"', maindesc[0].text)
    #     MainData["artwork_name"]=aname[0]
    # except:
    #     pass
    # maindesc=maindesc[0].text.split('.')
    
    # MainData["artwork_description"]=maindesc 
    # listToStr = ' '.join([str(elem) for elem in MainData["artwork_description"]])
    
    # MainData["artwork_description"]='<strong><br>Description:</strong><br>'+listToStr
    # MainData["artwork_description"]=MainData["artwork_description"].replace('\n','').encode('ascii', 'ignore').decode("utf-8").replace('"','')
    
    # title=maindesc[0].split(',')
    
    # df = pd.read_excel('/root/artwork/deploydirnew/docs/fineart_materials.xls')
    # mylist1 = df['material_name'].tolist()
    # print(maindesc)
    # print(len(maindesc))
    # # print(maindesc[0])
    # # print(maindesc[1])
    # # print(maindesc[2])
    
    # for x in range(len(maindesc)):
    #     for t in range(len(mylist1)):
    #         if(maindesc[x].lower().find(mylist1[t].replace("'","").lower())!=-1):
    #             MainData["artwork_category"]=df['material_category'][t]
    #             MainData["artwork_materials"] = mylist1[t]
    #     if(maindesc[x].lower().find("signed")!=-1):
    #         MainData["artwork_markings"]=maindesc[x]
    #     if(maindesc[x].lower().find("wear")!=-1 or maindesc[x].lower().find("fine")!=-1):
    #         MainData["artwork_condition_in"]=maindesc[x]
    #     if(maindesc[x].lower().find(" cm")!=-1 or maindesc[x].lower().find(" inches")!=-1 or maindesc[x].lower().find(" mm")!=-1):        
    #         #measure=maindesc[x].split('x')
    #         new_string = ' '.join([w for w in maindesc[x].split() if len(w)<5])
    #         MainData["artwork_size_notes"]=new_string
    #         if new_string.find("cm") != -1:
    #             MainData["auction_measureunit"] = "cm"
    #             d=new_string.replace('cm','').strip()
    #             d=d.split('x')
    #             try:
    #                 MainData["artwork_measurements_height"]=d[0]
    #                 MainData["artwork_measurements_width"]=d[1]
    #             except:
    #                 pass

                
    #         elif(new_string.find("mm")!= -1):
    #             MainData["auction_measureunit"] = "mm"
    #             #MainData["auction_measureunit"] = "cm"
    #             d=new_string.replace('cm','').strip()
    #             d=d.split('x')
    #             try:
    #                 MainData["artwork_measurements_height"]=d[0]
    #                 MainData["artwork_measurements_width"]=d[1]
    #             except:
    #                 pass
    #         else:
    #             MainData["auction_measureunit"] = "inches"
    #            # MainData["auction_measureunit"] = "cm"
    #             d=new_string.replace('cm','').strip()
    #             d=d.split('x')
    #             try:
    #                 MainData["artwork_measurements_height"]=d[0]
    #                 MainData["artwork_measurements_width"]=d[1]
    #             except:
    #                 pass
    # for q in range(len(title)):
            
    #     for t in range(len(mylist1)):
    #         if(title[q].lower().find(mylist1[t].replace("'","").lower())!=-1):
    #             MainData["artwork_category"]=df['material_category'][t]
    #             MainData["artwork_materials"] = title[q].replace('"','')
                
    #         if(title[q].lower().find("signed")!=-1):
    #             MainData["artwork_markings"]=title[q].replace('"','')
        
    #     #c-common-lot-show-carousel__link
    # imglinks =soup.find_all("a", {"class": "c-common-lot-show-carousel__link"})
    # # for u in imglinks:
    # #     v=u.find('img')
    # #     print(v['src'])
    # for uu in range(0,len(imglinks)-1):
    #     dd="artwork_images"+str(uu+1)
    #     if(dd=='artwork_images7'):
    #     	break
    #     v=imglinks[uu].find('img')
        
    #     MainData[dd]=''
    #     just=v['src']
    #     MainData[dd]=just
    #     #print(imagelist[uu])

    # print(imglinks)
    # print(title)
    
    # #print(x22)
    
    # print(maindesc)
    # print(MainData)
    # print(dates)
    # auctionum=MainData["lot_origin_url"]
    # #x = re.search(r"/auctions/(.*)?lots", auctionum)
    # result = re.search('/auctions/(.*)/lots', auctionum)
    # result=result.group(1).replace('/','')
    # MainData["auction_num"]=result

    # #y=re.findall('/auctions/(.*)/lots',mainurl)
    # #x=re.findall('/a/(.*)?ic', mainurl) 
    # csvpath=csvpath+"/"+"Bukowskis"+"_"+MainData["auction_num"]+'.csv'
    # keys=["auction_house_name","auction_location","auction_num","auction_start_date","auction_end_date","auction_name","lot_num","sublot_num","price_kind","price_estimate_min","price_estimate_max","price_sold","artist_name","artist_birth","artist_death","artist_nationality","artwork_name","artwork_year_identifier","artwork_start_year","artwork_end_year","artwork_materials","artwork_category","artwork_markings","artwork_edition","artwork_description","artwork_measurements_height","artwork_measurements_width","artwork_measurements_depth","artwork_size_notes","auction_measureunit","artwork_condition_in","artwork_provenance","artwork_exhibited","artwork_literature","artwork_images1","artwork_images2","artwork_images3","artwork_images4","artwork_images5","artwork_images6","image1_name","image2_name","image3_name","image4_name","image5_name","lot_origin_url"]
        
    # file_exist=os.path.isfile(csvpath)
    # with open(csvpath, 'a', newline='') as output_file:
    #     keys=["auction_house_name","auction_location","auction_num","auction_start_date","auction_end_date","auction_name","lot_num","sublot_num","price_kind","price_estimate_min","price_estimate_max","price_sold","artist_name","artist_birth","artist_death","artist_nationality","artwork_name","artwork_year_identifier","artwork_start_year","artwork_end_year","artwork_materials","artwork_category","artwork_markings","artwork_edition","artwork_description","artwork_measurements_height","artwork_measurements_width","artwork_measurements_depth","artwork_size_notes","auction_measureunit","artwork_condition_in","artwork_provenance","artwork_exhibited","artwork_literature","artwork_images1","artwork_images2","artwork_images3","artwork_images4","artwork_images5","artwork_images6","image1_name","image2_name","image3_name","image4_name","image5_name","lot_origin_url"]
    #         #keys = MainData.keys()
    #     #print(keys)
    #     # print(type(MainData))
    #     dictwriter_object = DictWriter(output_file,fieldnames=keys)
    #     if not file_exist:
    #         dictwriter_object.writeheader()
    #         dictwriter_object.writerow(MainData)
    #         output_file.close()
    #     else:
    #         dictwriter_object.writerow(MainData)
    #         output_file.close()
    
    # print(lotno)

    # mydivs = soup.find("div", {"class": "c-lot-index__lots"})
    # listpaint=mydivs.find_all("div", {"class": "c-lot-index-lot js-market-lot-index-lot js-push-lot-index-lot"})
    # for v in listpaint:
    #     link=v.find("a", {"class": "c-lot-index-lot__link ga-lot-index-lot"})
    #     #print('\n')
    #     #print(link['href'])
    #     urllist.append('https://www.bukowskis.com/'+link['href'])
    
def updatestatus(auctionno, auctionurl):
    auctionurl = auctionurl.replace("%3A", ":")
    auctionurl = auctionurl.replace("%2F", "/")
    pageurl = "http://216.137.189.57:8080/scrapers/finish/?scrapername=Cornette&auctionnumber=%s&auctionurl=%s&scrapertype=2"%(auctionno, urllib.parse.quote(auctionurl))
    pageResponse = None
    try:
        pageResponse = urllib.request.urlopen(pageurl)
    except:
        print ("Error: %s"%sys.exc_info()[1].__str__())  
    
   
            

if __name__ == "__main__":
    if sys.argv.__len__() < 3:
        print("Insufficient parameters")
        sys.exit()
    auctionurl = sys.argv[1]
    auctionnumber = sys.argv[2]
    csvpath = sys.argv[3]
    #pagesneeded=sys.argv[4]
    pagesneeded = 5
    acdate,acname,acloc,acno=getitemurls(auctionurl,pagesneeded)
    #print(urllist)
    for v in urllist:
        getitemdetails(v,csvpath,acdate,acname,acloc,acno)
    #getitemdetails()
    #obj,x22,acname=getitemurls(auctionurl,pagesneeded)
    
    #print(urllist)
    #getitemdetails(urllist[0])
    
    # for v in obj:
    #     getitemdetails(v,csvpath,x22,acname)
    updatestatus(auctionnumber, auctionurl)

    #python cornette.py "https://auction.cornettedesaintcyr.fr/catalogue/116114" 2575 C:/Users/Mrugank/Downloads/Selenium/testscrap 1            
