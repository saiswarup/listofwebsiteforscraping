from email import header
import os
import xlrd
import requests
import html5lib
from bs4 import BeautifulSoup
import csv
import sys
import re
import pandas as pd
from datetime import datetime
from cryptography.fernet import Fernet
from csv import DictWriter
from dateutil import parser
import json
import pprint
from quantulum3 import parser as qtlum
import urllib
urllist=[]
AuctionDate=''
AuctionName=''


def encryptFilename(filename):
        k = Fernet.generate_key()
        f = Fernet(k)
        encfilename = f.encrypt(filename.encode())
        return encfilename

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
    r=requests.get(mainurl,allow_redirects=False)


    soup = BeautifulSoup(r.text,'html.parser')
    

    mydivs = soup.find("div", {"id": "lots"})
    lotboxes=mydivs.select('.lotBox')
    for i in  lotboxes:
        x=i.select_one('a')
        x=x['href']
        #print('https://www.ponteonline.com'+x)
        urllist.append('https://www.ponteonline.com'+x)
    auctionname= soup.find("div", {"class": "page-title-name"})
    AuctionName=auctionname.select_one('h1').text
    auctiondate=soup.find("p", {"class": "h4-alike"})
    AuctionDate=auctiondate.text
    AuctionLocation=''    
    auctionno=soup.find("h5", {"class": "text-white"}).text
    auctionlocation=soup.find_all("div", {"class": "acd-des additional_info_blocks"})
    for u in auctionlocation:
        tt=u.find_all("p", {"class": "auctionTextContainer"})
        for v in tt:
            if(v.text.find('Location:')!=-1):
                
                AuctionLocation=v.text.split('Location:')[1].strip()
            # if(v.text.startswith('Location:')):
            #     print(v.split('Location:')[1].strip())

        
            
            
                # if(vv.find('strong').text=='Location'):
                #     print(vv.text)

    #auctionlocation=auctionlocation.select('.auctionTextContainer')
    #print(auctionlocation)
    return AuctionDate,AuctionName,auctionno,AuctionLocation  

        #print(i)
    #print(mydivs)
        

        
        

        
        
    # return urllist
        

    
def getitems(AuctionInfo,csvpath,dictobj):
    MainData={}
    MainData=AuctionInfo
    #csvpath=csvpath+"/"+"LempertzAuctions"+"_"+MainData["auction_num"]+'.csv'
    
    #print(dictobj)
    #print(MainData)
    lots=dictobj['lots']
    cne=0
    for i in lots:
        MainData["lot_num"]=i["number"]
        MainData["artwork_category"]=''
    #MainData["artcategory"]=''
        
        MainData["auction_end_date"]=""
        MainData["sublot_num"]=""
        MainData["price_estimate_max"]=""
        MainData["artwork_year_identifier"]=""
        MainData["artwork_end_year"]=""
        MainData["price_kind"]=''
        MainData["price_sold"]=''
        
        MainData["artwork_description"]=''
        MainData["artwork_provenance"]=''
        MainData["artwork_literature"]=''
        MainData["artwork_exhibited"]=''
        MainData["lot_origin_url"]=''
        MainData["artist_nationality"]=''
        MainData["artist_birth"]=''
        MainData["artist_death"]=''
        MainData["artist_name"]=''
        MainData["artwork_name"]=''
        MainData["artwork_size_notes"]=''
        MainData["artwork_materials"]=''
        MainData["artwork_markings"]=''
        MainData["artwork_edition"]=''
        MainData["artwork_condition_in"]=''
        MainData["auction_measureunit"]=''
        #MainData["estimaterange"]=''
        MainData["artwork_measurements_height"]=''
        MainData["artwork_measurements_width"]=''
        MainData["artwork_measurements_depth"]=''
        #MainData["imgdescription"]=''
        MainData["artwork_images1"]=''
        MainData["artwork_images2"]=''
        MainData["artwork_images3"]=''
        MainData["artwork_images4"]=''
        MainData["artwork_images5"]=''
        MainData["image1_name"]=''
        MainData["image2_name"]=''
        MainData["image3_name"]=''
        MainData["image4_name"]=''
        
        print("Processing lot number %s"%i)
        description=i['description'].split('\r\n\r\n')
        
        x12=i['session_end']
        x22=parser.parse(x12)
        #print(type(x22))
        day=x22.month
        month=x22.day
        year=x22.year
        x22=x22.replace(year,day,month)
        
        x22=x22.strftime("%d-%b-%y")
        MainData["auction_end_date"]=x22

        for c in range (len(description)):
            if(c==1):
                dd=description[c].split('\r\n')
                MainData['artwork_name']=dd[0]
                datee=description[c]
                r=r"\d{4}"
                res=re.findall(r,datee)
                if(res is not None):
                    try:
                        MainData["artwork_start_year"]=res[0]
                    except:
                        pass

            if(description[c].find(' cm ')!=-1 or description[c].find(' inches ')!=-1 or description[c].find(' mm ')!=-1):
                # regex=r"(?<!\S)+[\-\+]?[0-9]*(\.[0-9]+)?(?:,[\-\+]?[0-9]*(\.[0-9]+)?)? ?x ?[\-\+]?[0-9]*(\.[0-9]+)?(?:,[\-\+]?[0-9]*(\.[0-9]+)?)?(?: ?x ?[\-\+]?[0-9]*(\.[0-9]+)?(?:,[\-\+]?[0-9]*(\.[0-9]+)?)?)*"
                # stt=(description[c])
                # res=re.findall(regex,stt)
                quants = qtlum.parse(description[c])
                try:
                    sizenote=str(quants[0].value)+'x'+str(quants[1].value)+quants[1].unit.name
                    MainData["auction_measureunit"]='cm' if quants[1].unit.name=='centimetre' else 'inches' if quants[1].unit.name=='inches' else 'unknown'
                    MainData["artwork_measurements_height"]=quants[0].value
                    MainData["artwork_measurements_width"]=quants[1].value
                    MainData["artwork_size_notes"]=sizenote
                except:
                    pass

                #print(quants)

            #print(description[c])
        if(i['estimate']=='' or i['estimate'] is None and i['hammerprice']=='' or i['hammerprice'] is None or i['estimate']==0):
            MainData['price_kind']='unknown'
        elif(i['hammerprice']=='' or i['hammerprice'] is None and i['estimate'] !='none' or i['hammerprice']==0):
            MainData['price_kind']='estimate'
        else:
            MainData['price_kind']='price realised'

        MainData['price_sold']=i['hammerprice']
        MainData['price_estimate_max']=i['estimate_to']
        MainData['price_estimate_min']=i['estimate']
        listToStr = ' '.join([str(elem) for elem in description[1:4]])

        MainData["artwork_description"]='<strong><br>Description:</strong><br>'+listToStr

        t = description[2]
        v=re.findall("[A-Z].*?[\.!?]", t, re.MULTILINE | re.DOTALL )
        #print(v)
        MainData["lot_origin_url"]=i['link']
        MainData["artist_name"]=i['title']
        MainData["artwork_images1"]=i['identifier'].replace('-thumb','')
        if(i['provenance'] is not None):
            MainData["artwork_provenance"]=i['provenance']
        if(i['literature'] is not None):
            MainData["artwork_literature"]=i['literature']
        if(i['exhibitions'] is not None):
            MainData["artwork_exhibited"]=i['exhibitions']
        
        #df = pd.read_excel('docs/fineart_materials.xls')
        df = pd.read_excel('/root/artwork/deploydirnew/docs/fineart_materials.xls')
        mylist1 = df['material_name'].tolist()
        for k in range(len(v)):
            for t in range(len(mylist1)):
                if(v[k].lower().startswith(mylist1[t].replace("'","").lower())):
                    MainData["artwork_category"]=df['material_category'][t]
                    MainData["artwork_materials"] = v[k]
            if v[k].startswith('Signed'):
                try:
                    MainData["artwork_markings"]=v[k]+v[k+1]
                except:
                    MainData["artwork_markings"]=v[k]

            if (v[k].find("condition") != -1 ):
                MainData["artwork_condition_in"]=v[k]
            if (v[k].lower().find("edition") != -1 ):
                MainData["artwork_edition"]=v[k]

        #print(MainData)
        keys=["auction_house_name","auction_location","auction_num","auction_start_date","auction_end_date","auction_name","lot_num","sublot_num","price_kind","price_estimate_min","price_estimate_max","price_sold","artist_name","artist_birth","artist_death","artist_nationality","artwork_name","artwork_year_identifier","artwork_start_year","artwork_end_year","artwork_materials","artwork_category","artwork_markings","artwork_edition","artwork_description","artwork_measurements_height","artwork_measurements_width","artwork_measurements_depth","artwork_size_notes","auction_measureunit","artwork_condition_in","artwork_provenance","artwork_exhibited","artwork_literature","artwork_images1","artwork_images2","artwork_images3","artwork_images4","artwork_images5","image1_name","image2_name","image3_name","image4_name","image5_name","lot_origin_url"]
        
        file_exist=os.path.isfile(csvpath)
        with open(csvpath, 'a', newline='') as output_file:
            keys=["auction_house_name","auction_location","auction_num","auction_start_date","auction_end_date","auction_name","lot_num","sublot_num","price_kind","price_estimate_min","price_estimate_max","price_sold","artist_name","artist_birth","artist_death","artist_nationality","artwork_name","artwork_year_identifier","artwork_start_year","artwork_end_year","artwork_materials","artwork_category","artwork_markings","artwork_edition","artwork_description","artwork_measurements_height","artwork_measurements_width","artwork_measurements_depth","artwork_size_notes","auction_measureunit","artwork_condition_in","artwork_provenance","artwork_exhibited","artwork_literature","artwork_images1","artwork_images2","artwork_images3","artwork_images4","artwork_images5","image1_name","image2_name","image3_name","image4_name","image5_name","lot_origin_url"]
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
        
        
        # cne+=1
        # if(cne==2):
        #     break
        # print(MainData["auction_num"])
        
    
        
def getitemdetails(mainurl,csvpath):
    
    MainData={}
    MainData["artwork_category"]=''
    #MainData["artcategory"]=''
    MainData["auction_location"]="Dallas"
    MainData["auction_num"]=''
    MainData["lot_num"]=''
    MainData["auction_house_name"]="HeritageAuctions"
    MainData["auction_name"]=""
    MainData["auction_end_date"]=""
    MainData["sublot_num"]=""
    MainData["price_estimate_max"]=""
    MainData["artwork_year_identifier"]=""
    MainData["artwork_end_year"]=""
    MainData["price_kind"]=''
    MainData["price_sold"]=''
    MainData["auction_start_date"]=''
    MainData["artwork_description"]=''
    MainData["artwork_provenance"]=''
    MainData["artwork_literature"]=''
    MainData["artwork_exhibited"]=''
    MainData["lot_origin_url"]=''
    MainData["artist_nationality"]=''
    MainData["artist_birth"]=''
    MainData["artist_death"]=''
    MainData["artist_name"]=''
    MainData["artwork_name"]=''
    MainData["artwork_size_notes"]=''
    MainData["artwork_materials"]=''
    MainData["artwork_markings"]=''
    MainData["artwork_edition"]=''
    MainData["artwork_condition_in"]=''
    MainData["auction_measureunit"]=''
    #MainData["estimaterange"]=''
    MainData["artwork_measurements_height"]=''
    MainData["artwork_measurements_width"]=''
    MainData["artwork_measurements_depth"]=''
    #MainData["imgdescription"]=''
    MainData["artwork_images1"]=''
    MainData["artwork_images2"]=''
    MainData["artwork_images3"]=''
    MainData["artwork_images4"]=''
    MainData["artwork_images5"]=''
    MainData["image1_name"]=''
    MainData["image2_name"]=''
    MainData["image3_name"]=''
    MainData["image4_name"]=''

    x = re.search(r"/a/(.*)?ic4", mainurl)
    x=re.findall('/a/(.*)?ic', mainurl) 
    lotdet=x[0].replace(".s?", "")
    y=re.findall('/itm/(.*)/',mainurl)
    
    checkcat=re.findall('https://(.*).ha.com', mainurl) 
    #print(checkcat[0])
    #print(y[0].split("/")[0])
    
    MainData["artwork_category"]=checkcat[0]
    #MainData["artcategory"]=y[0].split("/")[0]
    MainData["auction_num"]=lotdet.split("-")[0]
    MainData["lot_num"]=lotdet.split("-")[1]
    #print(MainData)
    headers={
    "Host": checkcat[0]+".ha.com",
    "User-Agent":
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:96.0) Gecko/20100101 Firefox/96.0",

    "Connection": "keep-alive",
    "Cookie":
      "KP_UIDz-ssn=02jQsD8fIro8w5jKY7bi6DC9LjIRLgmabR5aUjq1wT54zZES8DAMqZU59GQ5NyI5ZUz2e0DR5CNGvf6tlO4LZ6XpuIxJQV79gL5AEVBbDfsjOv0GkoEtsWnBmPO5Uw9RCCsx6AUUT5LSsvoPhtQiZndNI91; KP_UIDz=02jQsD8fIro8w5jKY7bi6DC9LjIRLgmabR5aUjq1wT54zZES8DAMqZU59GQ5NyI5ZUz2e0DR5CNGvf6tlO4LZ6XpuIxJQV79gL5AEVBbDfsjOv0GkoEtsWnBmPO5Uw9RCCsx6AUUT5LSsvoPhtQiZndNI91; CNo=TkxzUHpSZzYvT0JXY04wPS5zbmZDdVBmRFJzdCtOeEZZLlFRdFJvcis4TTlBQmp5NDVKY0hpR1E9PQ%3D%3D; OR=418678472; SR=https%3A%2F%2Fmail.google.com%2F; RawSR=https%3A%2F%2Fmail.google.com%2F; OptanonConsent=isGpcEnabled=0&datestamp=Thu+Jan+20+2022+23%3A48%3A37+GMT%2B0530+(India+Standard+Time)&version=6.22.0&isIABGlobal=false&hosts=&landingPath=NotLandingPage&groups=1%3A1%2C2%3A1%2C3%3A1%2C4%3A1&AwaitingReconsent=false&geolocation=IN%3BMH; s_fid=1000C0280CDC2DC8-2782E51E37004D79; s_nr=1642702716034-Repeat; _ga=GA1.2.624529090.1642501612; _gid=GA1.2.703807483.1642501612; _gcl_au=1.1.220912212.1642501612; s_vi=[CS]v1|30F34AF6A9E67C89-40000DE65EA8D346[CE]; OptanonAlertBoxClosed=2022-01-20T18:18:36.822Z; cto_bundle=o7fIM19zNFQyQ0pkZjI5ZUFaTjlJb2NLSFJYb2Y5Nm54ZGlqZXYlMkJSR2hGWGdtMVhhR0dXd2FKJTJCMTJTNVBDY3ZUWnEzelRsR0gxSWZreGF0TzVQWDdVTlJCWE5IJTJCYmlpV0EwVncxNDUwSDQ1Z1JsMnhxdXVYOTZwSGJMNDlqb1VYWnZBVzZhZXl1byUyRlhRJTJCaFBadXJ6cm5sTkhBJTNEJTNE; anon-up=a%3A11%3A%7Bs%3A9%3A%22viewAdult%22%3Bi%3A0%3Bs%3A3%3A%22rpp%22%3Bi%3A100%3Bs%3A4%3A%22erpp%22%3Bs%3A2%3A%2224%22%3Bs%3A4%3A%22vrpp%22%3Bi%3A25%3Bs%3A6%3A%22comics%22%3Ba%3A2%3A%7Bs%3A10%3A%22searchView%22%3Bs%3A7%3A%22gallery%22%3Bs%3A14%3A%22bidBuySearchIn%22%3Bs%3A9%3A%22SI_Titles%22%3B%7Ds%3A10%3A%22bidBuySort%22%3Bs%3A0%3A%22%22%3Bs%3A11%3A%22archiveSort%22%3Bs%3A0%3A%22%22%3Bs%3A17%3A%22hideWantlistModal%22%3Bi%3A0%3Bs%3A18%3A%22haliveCurrencyCode%22%3Bs%3A3%3A%22USD%22%3Bs%3A17%3A%22haliveHideYouTube%22%3Bs%3A1%3A%220%22%3Bs%3A15%3A%22disabledDialogs%22%3Bs%3A1%3A%22%7C%22%3B%7D; SessionID=13qi54l5a6g3itjbumr5rl11q3; test=123; LastSessionHit=1642702648; TS01bf530f=01b44f9845902442447d06147695234751ab5989b10bd610896a408d70870e7980759e2a46402c6f13747173a8523a4effd4266188; TS01bb2cd9=01b44f98459a7d8764e5805feac59a09363c9f17f49da6005ad2b02bc22630470c2b4d2bac195c686da19154904bbc66b1e885ea1f; js=1; s_custnum=0; s_cc=true; s_sq=%5B%5BB%5D%5D; _gat=1",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
  }

    response=requests.get(mainurl, headers=headers, allow_redirects=False)
    soup = BeautifulSoup(response.text,'html.parser')
    mainDiv = soup.find("div", {"class": "content"})
    linkpath=soup.find("div",{"class":"page-content"})
    breadcrumb=linkpath.select_one(".breadcrumb-bar")
    spanloc=breadcrumb.select(".breadcrumb-location")
    MainData["auction_name"]=spanloc[2].select_one('.breadcrumb-location-name').getText()
    lotDiv=mainDiv.select_one('.lot-picker')
    itemname = mainDiv.find("h1")
    
    if(checkcat[0]!='fineart'):
        #s[s.find("(")+1:s.find(")")]
        m = re.search(r"[12]\d{3}",itemname.getText())
        try:
            MainData["artwork_start_year"]=m.group(0)
        except:
            pass
        #artworkname
        brackdata=itemname.getText()[itemname.getText().find("(")+1:itemname.getText().find(")")]
        if(brackdata is not None):
            name=brackdata.split(",")
            MainData["artist_name"]=name[0]
        else:
            t1=itemname.getText().split(",")
            MainData["artist_name"]=t1[1]
        MainData["artwork_name"]=itemname.getText()
        price=''
        bidprice=mainDiv.select_one(".price-data")
        try:
            price=bidprice.find("strong").getText()
        except:
            price="Not Available"
        
        if(price == ""):
            MainData["price_kind"] = "price realized"
            MainData["price_sold"]=price
        else:
            MainData["price_kind"] = "estimate"
            MainData["price_estimate_min"] = price
        description=mainDiv.select_one("#auction-description")
        auctioninfo =mainDiv.select_one("#auction-info")
        auctiondates = auctioninfo.select_one(".auction-dates")
        year = auctiondates.select_one(".box-header").getText()
        dates = auctiondates.find("strong").getText()
        
        #MainData["auction_start_date"] = dates + "-" + year
        date1 = datetime.strptime(dates + "-" + year, '%b %d %Y')
        MainData["auction_start_date"]=date1

        desctext = description.find("span");
        MainData["artwork_description"] = "<strong><br>Description:</strong><br>"+desctext.getText().replace("\n", "")
        MainData["lot_origin_url"]=mainurl
        galleryid=mainDiv.select_one(".gallery-view-nav")
        try:
            imagelist=galleryid.find_all("a")
            # imagedesc=imagelist[0].find("img")["alt"]
            # MainData["imgdescription"]=imagedesc
            #print(len(imagelist))
            for uu in range(0,len(imagelist)-1):
                if uu+1 > 5:
                    break
                dd="artwork_images"+str(uu+1)
                MainData[dd]=''
                just=imagelist[uu].find("img")["data-src"]
                MainData[dd]=just
                #print(imagelist[uu])
        except:
            pass
        #print(MainData)
    else:
        price=''
        dimensionregex='';
        # with open ("DIMENSION_WORDS_PATTERN.txt","r") as dimfile:
        #     dimensionregex=dimfile.read()
        #     dimfile.close()

        bidprice=mainDiv.select_one(".price-data")
        try:
            price=bidprice.find("strong").getText()
        except:
            MainData["price_kind"] = "unknown"
            
                           
        if(price == ""):
            MainData["price_kind"] = "unknown"
            MainData["price_sold"]=price
        
        else:
            MainData["price_kind"] = "pricerealized"
            MainData["price_estimate_min"] = price

        description=mainDiv.select_one("#auction-description")
        auctioninfo =mainDiv.select_one("#auction-info")
        auctiondates = auctioninfo.select_one(".auction-dates")
        year = auctiondates.select_one(".box-header").getText()
        dates = auctiondates.find("strong").getText()
        x12= dates + "-" + year
        x22=parser.parse(x12)
        x22=x22.strftime("%d-%b-%y")
        MainData["auction_start_date"]=x22

        #MainData["auction_start_date"] = MainData["auction_start_date"].replace(",","-")
        #date1 = datetime.strptime(dates + "-" + year, '%b %d %Y')
        #MainData["auction_start_date"]=date1
        desctext = description.find("span");
        MainData["artwork_description"] ="<strong><br>Description:</strong><br>"+ desctext.getText().replace("\n", "")
        dxtarray = desctext.getText().split("\n");
        MainData["artwork_provenance"] = []
        MainData["artwork_literature"] = []
        MainData["artwork_exhibited"] = []
        MainData["lot_origin_url"]=mainurl
        #df = pd.read_excel('docs/fineart_materials.xls')
        df = pd.read_excel('/root/artwork/deploydirnew/docs/fineart_materials.xls')
        mylist1 = df['material_name'].tolist()
        for k in range(len(dxtarray)):
            
            for t in range(len(mylist1)):
                if(dxtarray[k].lower()==mylist1[t].replace("'","").lower()):
                    MainData["artwork_category"]=df['material_category'][t]
                    MainData["artwork_materials"] = mylist1[t]
                    
            
            if(dxtarray[k].find("(") != -1 and dxtarray[k].find(")") != -1 and not dxtarray[k].find("inches") != -1 and not dxtarray[k].find("cm") != -1):
                crc=dxtarray[k][dxtarray[k].find("(")+1:dxtarray[k].find(")")]
                MainData["artist_nationality"]=crc.split(",")[0]
                if(len(crc.split(","))>1):
                    MainData["artist_birth"]=crc.split(",")[1].split("-")[0]
                    if(len(crc.split(",")[1].split("-"))>1):
                        try:
                            MainData["artist_death"]=crc.split(",")[1].split("-")[1]
                        except:
                            pass
                MainData["artist_name"]=dxtarray[k].split("(")[0]
                MainData["artwork_name"]=dxtarray[k+1]
                if(len(dxtarray[k+1].split(','))>1):
                    MainData["artwork_start_year"]=dxtarray[k+1].split(',')[1]
            if (dxtarray[k].find("(") != -1 and dxtarray[k].find(")") != -1 or  dxtarray[k].find("inches") != -1 or  dxtarray[k].find("cm") != -1):
                #MainData["artworkdet"]=dxtarray[k]
                if dxtarray[k].find("cm") != -1:
                    MainData["auction_measureunit"] = "cm"
                elif(dxtarray[k].find("mm")!= -1):
                    MainData["auction_measureunit"] = "mm"
                else:
                    MainData["auction_measureunit"] = "inches"
                tee=dxtarray[k][dxtarray[k].find("(")+1:dxtarray[k].find(")")]
                #MainData["artwork_measurements_height"]=tee
                MainData["artwork_size_notes"]=dxtarray[k]
                try:
                    r1=tee.replace("cm","")
                    r1=tee.replace("mm","")
                    r1=r1.split("x")
                    MainData["artwork_measurements_height"]=r1[0]
                    if(len(r1)>=1):
                        MainData["artwork_measurements_width"]=r1[1].replace("cm","")
                        if(len(r1)>1):
                            MainData["artwork_measurements_depth"]=r1[2].replace("cm","")                       

                    #MainData["artwork_measurements_width"]=r1[0]
                except:
                    pass
   
            if (dxtarray[k].startswith("Signed")):
                MainData["artwork_markings"] = dxtarray[k]
            if(dxtarray[k].startswith("PROVENANCE:") or dxtarray[k].startswith('Provenance:') ):
                for index in range(k,len(dxtarray)):
                    if(dxtarray[index] == ""):
                        break
                    else:
                        save=dxtarray[index].replace('\n','')
                        MainData["artwork_provenance"].append(save)
            if(dxtarray[k].startswith("LITERATURE:") or dxtarray[k].startswith('Literature:') ):
                for index in range(k,len(dxtarray)):
                    if(dxtarray[index] == ""):
                        break
                    else:
                        save=dxtarray[index].replace('\n','')
                        MainData["artwork_literature"].append(save)
            if(dxtarray[k].startswith("EXHIBITED:") or dxtarray[k].startswith('Exhibited') ):
                for index in range(k,len(dxtarray)):
                    if(dxtarray[index] == ""):
                        break
                    else:
                        save=dxtarray[index].replace('\n','')
                        MainData["artwork_exhibited"].append(save)
            if(dxtarray[k].startswith("Ed.") or dxtarray[k].startswith("Edition")):
                MainData["artwork_edition"] = dxtarray[k]
            if(dxtarray[k].startswith("Estimate:") or dxtarray[k].startswith("ESTIMATE:")):
                MainData["price_estimate_min"]=dxtarray[k].split("Estimate:")[0]
            
        galleryid=mainDiv.select_one(".gallery-view-nav")
        try:
            imagelist=galleryid.find_all("a")
            # imagedesc=imagelist[0].find("img")["alt"]
            # MainData["imgdescription"]=imagedesc
            #print(len(imagelist))
            for uu in range(0,len(imagelist)-1):
                if uu+1 > 5:
                    break
                dd="artwork_images"+str(uu+1)
                MainData[dd]=''
                just=imagelist[uu].find("img")["data-src"]
                MainData[dd]=just
                #print(imagelist[uu])
        except:
            pass
       
    if(MainData["artwork_provenance"]==[]):
        MainData["artwork_provenance"]=""
    if(MainData["artwork_literature"]==[]):
        MainData["artwork_literature"]=""
    if(MainData["artwork_exhibited"]==[]):
        MainData["artwork_exhibited"]=""
        
    #keys=["artwork_category","auction_num","auction_location","lot_num","auction_name","auction_house_name","auction_end_date","sublot_num","price_estimate_max","auction_measureunit","artwork_condition_in","artwork_year_identifier","artwork_end_year","price_kind","price_sold","auction_start_date","artwork_description","artwork_provenance","artwork_literature","artwork_exhibited","lot_origin_url","artist_nationality","price_estimate_min","artist_birth","artist_death","artist_name","artwork_name","artwork_measurements_depth","artwork_measurements_width","artwork_measurements_height","artwork_start_year","artwork_size_notes","artwork_materials","artwork_markings","artwork_edition","artwork_images1","artwork_images2","artwork_images3","artwork_images4","artwork_images5","artwork_images6"]
    keys=["auction_house_name","auction_location","auction_num","auction_start_date","auction_end_date","auction_name","lot_num","sublot_num","price_kind","price_estimate_min","price_estimate_max","price_sold","artist_name","artist_birth","artist_death","artist_nationality","artwork_name","artwork_year_identifier","artwork_start_year","artwork_end_year","artwork_materials","artwork_category","artwork_markings","artwork_edition","artwork_description","artwork_measurements_height","artwork_measurements_width","artwork_measurements_depth","artwork_size_notes","auction_measureunit","artwork_condition_in","artwork_provenance","artwork_exhibited","artwork_literature","artwork_images1","artwork_images2","artwork_images3","artwork_images4","artwork_images5","image1_name","image2_name","image3_name","image4_name","image5_name","lot_origin_url"]
    file_exist=os.path.isfile(csvpath)
    with open(csvpath, 'a', newline='') as output_file:
        keys=["auction_house_name","auction_location","auction_num","auction_start_date","auction_end_date","auction_name","lot_num","sublot_num","price_kind","price_estimate_min","price_estimate_max","price_sold","artist_name","artist_birth","artist_death","artist_nationality","artwork_name","artwork_year_identifier","artwork_start_year","artwork_end_year","artwork_materials","artwork_category","artwork_markings","artwork_edition","artwork_description","artwork_measurements_height","artwork_measurements_width","artwork_measurements_depth","artwork_size_notes","auction_measureunit","artwork_condition_in","artwork_provenance","artwork_exhibited","artwork_literature","artwork_images1","artwork_images2","artwork_images3","artwork_images4","artwork_images5","image1_name","image2_name","image3_name","image4_name","image5_name","lot_origin_url"]
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
            # file doesn't exist yet, write a header
        #dict_writer.writeheader()
        
            
            
def getdetailfromurl(url,AuctionDate,AuctionName,Auctionno,AuctionLocation,csvpath):
    
    r=requests.get(url,allow_redirects=False)
    soup = BeautifulSoup(r.text,'html.parser')
    mydivs = soup.find("div", {"class": "col-lg-5 port-information sm-mt-40"})
    heading=mydivs.select_one('.text-dark')
    heading=heading.text
    heading=heading.split('|')[0].replace('Lot n°','').strip()
    MainData={}
    MainData["artwork_category"]=''
    #MainData["artcategory"]=''
    MainData["auction_location"]=""
    MainData["auction_num"]=''
    MainData["lot_num"]=''
    MainData["auction_house_name"]="Il Ponte"
    MainData["auction_name"]=""
    MainData["auction_end_date"]=""
    MainData["sublot_num"]=""
    MainData["price_estimate_max"]=""
    MainData["artwork_year_identifier"]=""
    MainData["artwork_end_year"]=""
    MainData["price_kind"]=''
    MainData["price_sold"]=''
    MainData["auction_start_date"]=''
    MainData["artwork_description"]=''
    MainData["artwork_provenance"]=''
    MainData["artwork_literature"]=''
    MainData["artwork_exhibited"]=''
    MainData["lot_origin_url"]=''
    MainData["artist_nationality"]=''
    MainData["artist_birth"]=''
    MainData["artist_death"]=''
    MainData["artist_name"]=''
    MainData["artwork_name"]=''
    MainData["artwork_size_notes"]=''
    MainData["artwork_materials"]=''
    MainData["artwork_markings"]=''
    MainData["artwork_edition"]=''
    MainData["artwork_condition_in"]=''
    MainData["auction_measureunit"]=''
    #MainData["estimaterange"]=''
    MainData["artwork_measurements_height"]=''
    MainData["artwork_measurements_width"]=''
    MainData["artwork_measurements_depth"]=''
    #MainData["imgdescription"]=''
    
    MainData["artwork_images1"]=''
    MainData["artwork_images2"]=''
    MainData["artwork_images3"]=''
    MainData["artwork_images4"]=''
    MainData["artwork_images5"]=''
    MainData["image1_name"]=''
    MainData["image2_name"]=''
    MainData["image3_name"]=''
    MainData["image4_name"]=''
    MainData["auction_start_date"]=AuctionDate
    MainData["auction_name"]=AuctionName
    MainData["auction_num"]=Auctionno.split('Auction N.')[1]
    MainData["auction_location"]=AuctionLocation
        
    MainData["lot_num"]=heading
    portinfo = soup.find("div", {"class": "port-info"})
    imagelink=soup.find("div", {"class": "lotImageContainer"})
    imagelink=soup.find_all("div", {"class": "item"})
    for uu in range(0,len(imagelink)):
        if uu+1 > 5:
            break
        dd="artwork_images"+str(uu+1)
        MainData[dd]=''
        just=imagelink[uu].find("a")["data-src"]
        MainData[dd]='https://www.ponteonline.com'+just
        #print(imagelink[uu])
    # for link in imagelink:
        
    author=portinfo.select_one('.author')
    author=author.text
    estimaterange = portinfo.find("p", {"class": "h5-alike"})
    estimaterange=estimaterange.text.replace('Estimate','')
    estimaterange=estimaterange.split('-')
    MainData["price_estimate_min"]=estimaterange[0].replace('€','')
    
    try:
        MainData["price_estimate_max"]=estimaterange[1].replace('€','')
    except:
        pass
    pricesold = portinfo.find("h4", {"class": "theme-color mt-3"})
    if pricesold is not None:
        pricesold=pricesold.text.replace('Sold','').strip()
        MainData["price_sold"]=pricesold.replace('€','')
        if pricesold is not None and estimaterange is not None:
            MainData["price_kind"]='price realised'
        if estimaterange is None:
            MainData["price_kind"]='unknown'
        if(pricesold is  None and estimaterange is not None):
            MainData["price_kind"]='estimate'
    #print(portinfo)
    
    dates=author[author.find("(")+1:author.find(")")]
    #print(author)
    MainData["artist_name"]=author.split('(')[0]
    #print(dates)
    m=dates.split('-')
    m1 = re.search(r"\d{4}",m[0])
    if len(m)>1:
        m2 = re.search(r"\d{4}",m[1])
        if m2 is not None and m2.group(0) is not None:
            #print(m2.group(0))
            MainData["artist_death"]=m2.group(0)
    #print(m1.group(0))
    try:
        MainData["artist_birth"]=m1.group(0)
    except:
        pass
    portinfo = portinfo.find("p", {"class": "text-dark"})
    MainData["artwork_description"]=portinfo.text.split('\n')
    listToStr = ' '.join([str(elem) for elem in MainData["artwork_description"]])
    MainData["artwork_description"]='<strong><br>Description:</strong><br>'+listToStr
    
    desc=portinfo.text.split('\n')
    for x in range(len(desc)):
        if(x==0):

            MainData["artwork_name"]=desc[x]
        if(desc[x].find('Siglato')!=-1):
            MainData["artwork_markings"]=desc[x]
        if(desc[x].find('cm')!=-1 or desc[x].find('inches')!=-1 or desc[x].find('mm')!=-1 ):
            brac=desc[x][desc[x].find("(")+1:desc[x].find(")")]
            MainData["artwork_materials"]=desc[x].split(brac)[0].replace('(','')
            MainData["artwork_size_notes"]=brac
            MainData["artwork_measurements_height"]=brac.split('x')[0].replace('cm','')
            if(len(brac.split('x'))>1):
                MainData["artwork_measurements_width"]=brac.split('x')[1]
            MainData["auction_measureunit"]='cm' if 'cm' in desc[x] else 'inches'
        if(desc[x].find('Provenienza')!=-1):
            MainData["artwork_provenance"]=desc[x+1]
        x22=parser.parse(MainData["auction_start_date"])
    #print(type(x22))
    day=x22.month
    month=x22.day
    year=x22.year
    x22=x22.replace(year,day,month)
        
    x22=x22.strftime("%d-%b-%y")
    MainData["auction_start_date"]=x22
    #print(MainData)
    #csvpath=csvpath+"/"+"IlPonte"+"_"+MainData["auction_num"]+'.csv'
    keys=["auction_house_name","auction_location","auction_num","auction_start_date","auction_end_date","auction_name","lot_num","sublot_num","price_kind","price_estimate_min","price_estimate_max","price_sold","artist_name","artist_birth","artist_death","artist_nationality","artwork_name","artwork_year_identifier","artwork_start_year","artwork_end_year","artwork_materials","artwork_category","artwork_markings","artwork_edition","artwork_description","artwork_measurements_height","artwork_measurements_width","artwork_measurements_depth","artwork_size_notes","auction_measureunit","artwork_condition_in","artwork_provenance","artwork_exhibited","artwork_literature","artwork_images1","artwork_images2","artwork_images3","artwork_images4","artwork_images5","image1_name","image2_name","image3_name","image4_name","image5_name","lot_origin_url"]
        
    file_exist=os.path.isfile(csvpath)
    with open(csvpath, 'a', newline='') as output_file:
        keys=["auction_house_name","auction_location","auction_num","auction_start_date","auction_end_date","auction_name","lot_num","sublot_num","price_kind","price_estimate_min","price_estimate_max","price_sold","artist_name","artist_birth","artist_death","artist_nationality","artwork_name","artwork_year_identifier","artwork_start_year","artwork_end_year","artwork_materials","artwork_category","artwork_markings","artwork_edition","artwork_description","artwork_measurements_height","artwork_measurements_width","artwork_measurements_depth","artwork_size_notes","auction_measureunit","artwork_condition_in","artwork_provenance","artwork_exhibited","artwork_literature","artwork_images1","artwork_images2","artwork_images3","artwork_images4","artwork_images5","image1_name","image2_name","image3_name","image4_name","image5_name","lot_origin_url"]
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
   

def updatestatus(auctionno, auctionurl):
    auctionurl = auctionurl.replace("%3A", ":")
    auctionurl = auctionurl.replace("%2F", "/")
    pageurl = "http://216.137.189.57:8080/scrapers/finish/?scrapername=IlPonte&auctionnumber=%s&auctionurl=%s&scrapertype=2"%(auctionno, urllib.parse.quote(auctionurl))
    pageResponse = None
    try:
        pageResponse = urllib.request.urlopen(pageurl)
    except:
        print ("Error: %s"%sys.exc_info()[1].__str__())  
    

    
    

#print(urllist[0])

if __name__ == "__main__":
    if sys.argv.__len__() < 3:
        print("Insufficient parameters")
        sys.exit()
    auctionurl = sys.argv[1]
    auctionnumber = sys.argv[2]
    csvpath = sys.argv[3]
    pagesneeded=5
    imagepath = sys.argv[4]
    downloadimages = 0
    convertfractions = 0
    if sys.argv.__len__() > 5:
        downloadimages = sys.argv[5]
    if sys.argv.__len__() > 6:
        convertfractions = sys.argv[6]
    
    AuctionDate,AuctionName,auctionno,AuctionLocation =getitemurls(auctionurl,int(pagesneeded))
    for o in urllist:
        getdetailfromurl(o,AuctionDate,AuctionName,auctionno,AuctionLocation,csvpath)
    
    #getitems(MainInfo,csvpath,dictobj)
    # for v in range(len(urllist)):
    #     getitemdetails(urllist[v],csvpath)

    #getitemdetails(urllist,csvpath)
    # print(urllist)
    #getitemdetails(urllist[1],csvpath)
    updatestatus(auctionnumber, auctionurl)
    
#sample command>python ilponte.py "https://www.ponteonline.com/en/lot-list/auction/591" 591  /Users/saiswarupsahu/freelanceprojectchetan/ponte_591.csv /Users/saiswarupsahu/freelanceprojectchetan/1-5TNCV9 0 0
#https://www.ponteonline.com/en/lot-list/auction/534
