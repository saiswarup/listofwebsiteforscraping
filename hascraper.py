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

urllist=[]



def encryptFilename(filename):
        k = Fernet.generate_key()
        f = Fernet(k)
        encfilename = f.encrypt(filename.encode())
        return encfilename

def getitemurls(mainurl,pageno):
    checkcat=re.findall('https://(.*).ha.com', mainurl) 
    currenturl=mainurl
    getmainpage=mainurl.split("/c/")
    print(getmainpage)
    cn=pageno
    while(cn>=0):
        headers={
    "Host":checkcat[0]+".ha.com",
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

        r=requests.get(currenturl, headers=headers,allow_redirects=False)


        soup = BeautifulSoup(r.text,'html.parser')
    

        mydivs = soup.find("ul", {"class": "auction-items"})
        print(mydivs)
        li=mydivs.find_all('li')
        
        for i in li:
            print(i)
            url=i.select_one( ".new-window-link")
            try:
                url=url['href']
                urllist.append(url)
            except:
                print("SKIPPED ITEM")
        cn=cn-1
        searchdiv = soup.find("div", {"class": "search-results"})
        itempagination=searchdiv.find("div",{"class":"items-pagination"})
        nextpagelink=itempagination.select_one(".icon-right-triangle")
        try:
            nextpagelink=nextpagelink["href"]
            currenturl=getmainpage[0]+nextpagelink
            print(currenturl)
        except:
            print("No More Pages ,This was the last page")
            print(" Pages Able to Scrape="+str(cn+1)+" Out Of "+str(pageno)+" Pages")

        
        

        
        
    # return urllist
        

    

        
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
    MainData["artwork_images6"]=''
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
    print(MainData)
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
    #print(soup)
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
            print(len(imagelist))
            for uu in range(0,5):
                dd="artwork_images"+str(uu+1)
                MainData[dd]=''
                just=imagelist[uu].find("img")["data-src"]
                MainData[dd]=just
                print(imagelist[uu])
        except:
            pass
        print(MainData)
        
        
        
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
            print(len(imagelist))
            for uu in range(0,len(imagelist)-1):
                dd="artwork_images"+str(uu+1)
                if uu==6:
                    break
                MainData[dd]=''
                just=imagelist[uu].find("img")["data-src"]
                MainData[dd]=just
                print(imagelist[uu])
        except:
            pass

            
        
    if(MainData["artwork_provenance"]==[]):
        MainData["artwork_provenance"]=""
    if(MainData["artwork_literature"]==[]):
        MainData["artwork_literature"]=""
    if(MainData["artwork_exhibited"]==[]):
        MainData["artwork_exhibited"]=""
        
        
    #keys=["artwork_category","auction_num","auction_location","lot_num","auction_name","auction_house_name","auction_end_date","sublot_num","price_estimate_max","auction_measureunit","artwork_condition_in","artwork_year_identifier","artwork_end_year","price_kind","price_sold","auction_start_date","artwork_description","artwork_provenance","artwork_literature","artwork_exhibited","lot_origin_url","artist_nationality","price_estimate_min","artist_birth","artist_death","artist_name","artwork_name","artwork_measurements_depth","artwork_measurements_width","artwork_measurements_height","artwork_start_year","artwork_size_notes","artwork_materials","artwork_markings","artwork_edition","artwork_images1","artwork_images2","artwork_images3","artwork_images4","artwork_images5","artwork_images6"]
    keys=["auction_house_name","auction_location","auction_num","auction_start_date","auction_end_date","auction_name","lot_num","sublot_num","price_kind","price_estimate_min","price_estimate_max","price_sold","artist_name","artist_birth","artist_death","artist_nationality","artwork_name","artwork_year_identifier","artwork_start_year","artwork_end_year","artwork_materials","artwork_category","artwork_markings","artwork_edition","artwork_description","artwork_measurements_height","artwork_measurements_width","artwork_measurements_depth","artwork_size_notes","auction_measureunit","artwork_condition_in","artwork_provenance","artwork_exhibited","artwork_literature","artwork_images1","artwork_images2","artwork_images3","artwork_images4","artwork_images5","artwork_images6","image1_name","image2_name","image3_name","image4_name","image5_name","lot_origin_url"]
    #csvpath=csvpath+"/"+"HeritageAuctions"+"_"+MainData["auction_num"]+'.csv'
    file_exist=os.path.isfile(csvpath)
    with open(csvpath, 'a', newline='') as output_file:
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
            # file doesn't exist yet, write a header
        #dict_writer.writeheader()
        
        
        
            
    
        
            
            
        
            
            
            
                
                
                    
                    
                
                    
                
        print(MainData)
        #return MainData
                
        
        
        
            
            
            

    
    
#print(soup.prettify())
    

    
    
def updatestatus(auctionno, auctionurl):
    auctionurl = auctionurl.replace("%3A", ":")
    auctionurl = auctionurl.replace("%2F", "/")
    pageurl = "http://216.137.189.57:8080/scrapers/finish/?scrapername=Heritage&auctionnumber=%s&auctionurl=%s&scrapertype=2"%(auctionno, urllib.parse.quote(auctionurl))
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
    #pagesneeded=sys.argv[4]
    pagesneeded=5
    #imagepath = sys.argv[4]
    # downloadimages = 0
    # convertfractions = 0
    # if sys.argv.__len__() > 5:
    #     downloadimages = sys.argv[5]
    # if sys.argv.__len__() > 6:
    #     convertfractions = sys.argv[6]
    
    getitemurls(auctionurl,int(pagesneeded))
    for v in range(len(urllist)):
        getitemdetails(urllist[v],csvpath)
    #getitemdetails(urllist,csvpath)
    # print(urllist)
    #getitemdetails(urllist[1],csvpath)
    updatestatus(auctionnumber, auctionurl)
    
#sample command>python hascraper.py "https://fineart.ha.com/c/search-results.zx?N=3169+790+231+4294945366&ic=Items-ClosedAuctions-Closed-BrowseViewLots-071713" 2575 C:/Users/Mrugank/Downloads/Selenium/testscrap 1
