from email import header
from json.tool import main
import os
import xlrd
import requests
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
import pprint
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
    r=requests.get(mainurl,allow_redirects=False)
    
    #print(jsonresp)

    
    soup = BeautifulSoup(r.text,'html.parser')
    print(soup)
    mydivs = soup.find("div",{"id":"reactTimedCountdown"})
    catalogTitle= soup.find("h1",{"id":"catalogTitle"})
    catalogTitle=catalogTitle.text
    catalogdate= soup.find("div",{"class":"date-and-calendar"})
    x22=parser.parse(catalogdate.text.strip())
    x22=x22.strftime("%d-%b-%y")
    print(x22)
    

    print(catalogTitle.strip())
    x=mydivs['data-lotsdata']
    x=json.loads(x)
    x=x['auctionLotUserItemViewList']
    # for i in x:
    #     print(i)
    #     break
# print(x)
    

    #divlots = mydivs.find("div",{"id":"catalog-id"})
    
    
    #print(mydivs)
    # for i in divlots:
    #     print(i.find("a")[0])
    urllist=list(map(lambda x: x,x))
    return urllist,catalogTitle,x22
    
 
def getitemdetails(url,csvpath,catalogTitle,x22):
    print(url)
    x=url['itemView']['lotNumber']
    
    AuctionInfo={}
    MainData={}
    MainData["sublot_num"]="NA"
    MainData["price_estimate_max"]=""
    MainData["artwork_year_identifier"]=""
    MainData["artwork_end_year"]=""
    MainData['artist_name']=''
    MainData['artwork_literature']=''
    MainData['artwork_provenance']=''
    MainData['artwork_exhibited']=''
    MainData['price_estimate_max']=''
    MainData['price_estimate_max']=url['itemView']['estimateHigh']
    MainData['price_estimate_min']=''
    MainData['price_estimate_min']=url['itemView']['estimateLow']
    MainData['price_kind']=''
    MainData['price_sold']=''
    MainData['price_sold']=url['itemView']['priceResult']
    MainData['price_kind']='price realised' if (MainData['price_sold'] != '') else 'estimate'
    MainData["artwork_edition"]=''
    MainData["artwork_measurements_width"]=''
    MainData["artwork_measurements_height"]=''
    MainData["artwork_size_notes"]=''
    MainData["auction_measureunit"]=''
    MainData["artwork_measurements_depth"]=''
    
    
    #print(jsonresp)
    MainData['artist_nationality']=""
    
    
    # x22=parser.parse(date1)
    # x22=x22.strftime("%d-%b-%y")
    # print(x22)
    # maindiv=soup.find("div",{"class":"lot lot-details col-sm-6"})
    # print(maindiv.text.strip())
    MainData["auction_start_date"]=x22
    MainData["auction_end_date"]=""
    
    # lotno=maindiv.select_one(".lot-a-t")
    # MainData["lot_num"]=lotno.text
    # author=maindiv.find("h1",{"class":"lot-title cat-17"}).text
    # print(author)
    # try:
    MainData['artist_nationality']=""
    
    MainData['artist_birth']=""
    MainData['artist_death']=""

    #     name=re.search('(.*?)[\(](.*)[\)]',author).group(1)
    author=url['itemView']['artistDates'] 
    try:

        datecontent=re.search('(.*?)[\(](.*)[\)]',author).group(2)
        nation=re.search('(\d+)[\-](\d+)',datecontent)
        MainData['artist_nationality']=re.search('(.*?)[\(](.*)[\)]',author).group(1).replace(',','').strip()
        
        MainData['artist_birth']=nation.group(1)
        MainData['artist_death']=nation.group(2)
    except:
        pass
    MainData['artist_name']=''
    MainData['artist_name']=url['itemView']['artistFullName'].replace('<b>','').replace('</b>','')
    MainData["artwork_name"]= ""
    MainData["artwork_name"]=url['itemView']['pieceTitle'].replace('<b>','').replace('</b>','')
    MainData["artwork_year_identifier"] = ""
    MainData["artwork_start_year"] = ""
    MainData["artwork_end_year"] = ""
    MainData["artwork_materials"] = ""
    MainData["artwork_category"] = ""
    MainData["artwork_materials"] = url['itemView']['medium'].replace('<b>','').replace('</b>','')
    MainData["artwork_markings"] = ""
    MainData["artwork_markings"] = url['itemView']['conciseDescription'].replace('<b>','').replace('</b>','')
    MainData['artwork_description']='<strong><br>Description:</strong><br>'+str(url['itemView']['description']).replace('\n','')
    MainData['artwork_condition_in']=url['itemView']['condition'].replace('<i>','').replace('</i>','')
    
    #df = pd.read_excel('/root/artwork/deploydirnew/docs/fineart_materials.xls')
    df = pd.read_excel('docs/fineart_materials.xls')
    mylist1 = df['material_name'].tolist()
    for t in range(len(mylist1)):

        if(MainData["artwork_materials"].lower().find(mylist1[t].lower())!=-1):
                        
                
                    MainData["artwork_category"]=df['material_category'][t]
    MainData["artwork_provenance"] = url['itemView']['provenance'].replace('"',"").replace(":","").replace("(a) ","").replace('\n','').replace('<br>','')
    MainData["artwork_literature"] = url['itemView']['literature']
    MainData["artwork_exhibited"] = url['itemView']['exhibited']
    dimensions=url['itemView']['dimensions']
    
    if(MainData["artwork_provenance"].find('mm')!=-1 or MainData["artwork_provenance"].find('cm')!=-1 or MainData["artwork_provenance"].find('inches')!=-1):
                regex='Framed dimensions (\d+ \d[\/]\d) [x] (\d+ \d[\/]\d) [x] (\d) (inches|cm|mm)'
                regex2='Framed dimensions (\d+ \d[\/]\d|\d+) [x] (\d+ \d[\/]\d|\d+) [x] (\d+ \d[\/]\d|\d+|\d[\/]\d) (inches|cm|mm)'
                try:
                    sizenote=re.search(regex,MainData['artwork_provenance']).group(0)
                    MainData["auction_measureunit"]=re.search(regex,MainData['artwork_provenance']).group(4)
                    MainData["artwork_measurements_height"]=re.search(regex,MainData['artwork_provenance']).group(1)
                    MainData["artwork_measurements_width"]=re.search(regex,MainData['artwork_provenance']).group(2)
                    MainData["artwork_measurements_depth"]=re.search(regex,MainData['artwork_provenance']).group(3)
                    MainData["artwork_size_notes"]=sizenote
                except:
                    try:
                        print(MainData["artwork_provenance"])
                        sizenote=re.search(regex2,MainData['artwork_provenance']).group(0)
                        MainData["auction_measureunit"]=re.search(regex2,MainData['artwork_provenance']).group(4)
                        MainData["artwork_measurements_height"]=re.search(regex2,MainData['artwork_provenance']).group(1)
                        MainData["artwork_measurements_width"]=re.search(regex2,MainData['artwork_provenance']).group(2)
                        MainData["artwork_measurements_depth"]=re.search(regex2,MainData['artwork_provenance']).group(3)
                        MainData["artwork_size_notes"]=sizenote
                    except:
                        regex2='Framed dimensions(\d+ \d[\/]\d|\d+) [x] (\d+ \d[\/]\d|\d+) [x] (\d+ \d[\/]\d|\d+|\d[\/]\d) (inches|cm|mm)'
                        print(MainData["artwork_provenance"])
                        sizenote=re.search(regex2,MainData['artwork_provenance']).group(0)
                        MainData["auction_measureunit"]=re.search(regex2,MainData['artwork_provenance']).group(4)
                        MainData["artwork_measurements_height"]=re.search(regex2,MainData['artwork_provenance']).group(1)
                        MainData["artwork_measurements_width"]=re.search(regex2,MainData['artwork_provenance']).group(2)
                        MainData["artwork_measurements_depth"]=re.search(regex2,MainData['artwork_provenance']).group(3)
                        MainData["artwork_size_notes"]=sizenote
    if(dimensions is not None):
        dimensions=dimensions.replace('  ',' ')
        regex2='(\d+ \d[\/]\d|\d+) [x] (\d+ \d[\/]\d|\d+) (inches|cm|mm)'
        
        sizenote=re.search(regex2,dimensions).group(0)
        MainData["auction_measureunit"]=re.search(regex2,dimensions).group(3)
        MainData["artwork_measurements_height"]=re.search(regex2,dimensions).group(1)
        MainData["artwork_measurements_width"]=re.search(regex2,dimensions).group(2)
        #MainData["artwork_measurements_depth"]=re.search(regex2,dimensions).group(3)
        MainData["artwork_size_notes"]=sizenote

        
                    
                        
        
                


    
    # except:
    #     pass
    # lotdesc=maindiv.select(".lot-desc")
    # for x in lotdesc:
    #     lotdesc=x
    #     break
    
    # desclist=str(lotdesc).split("<br/>")
    # listToStr = ' '.join([str(elem) for elem in desclist])    
    # MainData['artwork_description']='<strong><br>Description:</strong><br>'+str(listToStr)
    # print(desclist)
    # df = pd.read_excel('fineart_materials.xls')
    # mylist1 = df['material_name'].tolist()
    # for i in range(len(desclist)):
    #     for t in range(len(mylist1)):
            
    #         #if(desclist[i].lower().find(mylist1[t].replace("'","").lower().replace("'",""))!=-1):
            
    #         #print(my_new_string)
    #         if(desclist[i].lower().find(mylist1[t].lower())!=-1):
                
            
    #             MainData["artwork_category"]=df['material_category'][t]
    #             #print(desclist[i].lower()[desclist[i].lower().find(mylist1[t].lower())])
    #             #MainData["artwork_materials"] = desclist[i].lower()[desclist[i].lower().find(mylist1[t].lower()):len(desclist[i].lower())]
    #             MainData["artwork_materials"] = mylist1[t].lower()+desclist[i].lower().split(mylist1[t].lower())[1].replace(",","")
    #             signedPattern = re.compile("(signed)|(unsigned)|(inscribed)", re.IGNORECASE)
    #             materialsparts = re.split(signedPattern, MainData["artwork_materials"])
    #             MainData["artwork_materials"] = materialsparts[0]

    #     if i==1:
    #         l=desclist[i]
    #         try:
    #             regx='(.*?)[\,][\s+](\d+)'
    #             #MainData["artwork_name"]=re.search(regx,l).group(1)
    #             MainData["artwork_name"]=desclist[i].replace("</strong>","")
           
    #             MainData["artwork_start_year"]=re.search(regx,l).group(2)
    #         except:
    #             pass
    #     if desclist[i].lower().find('signed')!=-1 or desclist[i].lower().find('unsigned')!=-1 or desclist[i].lower().find('inscribed')!=-1 :
                   
    #         MainData['artwork_markings']=re.search('(signed|unsigned|inscribed)(.*)' ,desclist[i].lower()).group(0)

    #     if(desclist[i].lower().find('numbered')!=-1):
    #         try:
    #             MainData["artwork_edition"]=re.search('numbered (\d+)/(\d+)', desclist[i]).group(1)+'By'+re.search('numbered (\d+)/(\d+)', desclist[i]).group(2)
    #         except:
    #             pass
        # if(desclist[i].find('mm')!=-1 or desclist[i].find('cm')!=-1 or desclist[i].find('inches')!=-1):
        #         quants = qtlum.parse(desclist[i])
        #         try:
        #             sizenote=str(quants[0].value)+'x'+str(quants[1].value)+quants[1].unit.name
        #             MainData["auction_measureunit"]='cm' if quants[1].unit.name=='centimetre' else 'inches' if quants[1].unit.name=='inches' else 'mm' if quants[1].unit.name=='millimetre' else 'unknown'
        #             MainData["artwork_measurements_height"]=quants[0].value
        #             MainData["artwork_measurements_width"]=quants[1].value
        #             MainData["artwork_size_notes"]=sizenote
        #         except:
        #             pass
    #     if desclist[i].lower().find('exhibited:')!=-1:
    #         MainData['artwork_exhibited']=str(desclist[i])
    #     if desclist[i].lower().find('provenance:')!=-1:
    #         MainData['artwork_provenance']=str(desclist[i])
    #     if desclist[i].lower().find('literature:')!=-1:
    #         MainData['artwork_literature']=str(desclist[i])
    # estimate=maindiv.select(".estimate")
    # print(estimate[0].text)
    # print(re.search('[Estimate][\£](\d+) [\-] [\£](\d+)',estimate[0].text.replace(',','')).group(1))
    # MainData['price_estimate_min']=re.search('[Estimate][\£](\d+) [\-] [\£](\d+)',estimate[0].text.replace(',','')).group(1)
    # MainData['price_estimate_max']=re.search('[Estimate][\£](\d+) [\-] [\£](\d+)',estimate[0].text.replace(',','')).group(2)
    # if(MainData['price_estimate_min']=='' and MainData['price_estimate_min']==''):
    #     MainData['price_kind']='unknown'
    # elif(MainData['price_estimate_min']!='' or MainData['price_estimate_max']!='' and MainData['price_sold']==''):
    #     MainData['price_kind']='estimate'
    # else:
    #     MainData['price_kind']='price realised'
    
    
    
    
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
   
    # for j in range( len(lotdesc)):
    #     if j==2:
    #         #print (lotdesc[j])
    #         o=lotdesc[j].find_all("p")
    #         #print()
    #         listToStr = str(o[0].text.replace("Condition Report","").replace("\n",""))
    #         MainData['artwork_condition_in']=str(listToStr)
    
    MainData["auction_location"]='Milford'
    MainData["auction_num"]=""
    try:
        
        MainData["auction_num"]=re.search("(\d+)(.*)",catalogTitle.strip()).group(1)
    except:
        MainData["auction_num"]="unknown"
    MainData["lot_num"]=x
    MainData["auction_house_name"]="Shannon's Fine Art Auctioneers"
    MainData["auction_name"]=catalogTitle.strip()
    
    
    listpaint=url['itemView']['photos']
    p=1

    for x in listpaint:
        if(p==5):
            break
        
        dd="artwork_images"+str(p)
        p+=1
        MainData[dd]=x['_links']['large']['href']
    # #+++++++++++++++++_________________+++++++++++++++++++++++_____________+++++++++++++++++++++
    MainData["lot_origin_url"]="https://www.shannons.com"+url['itemView']['linkLotURLRelative']
    # MainData['artwork_start_year']=''
    MainData['artwork_end_year']=''
    #csvpath=csvpath+"/"+"Shannons"+"_"+str(MainData["auction_num"])+'.csv'
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
    #+++++++++++++++++++++++++=_________________)))))))))))))))))))____________________________
    print(MainData)
    
def updatestatus(auctionno, auctionurl):
    auctionurl = auctionurl.replace("%3A", ":")
    auctionurl = auctionurl.replace("%2F", "/")
    pageurl = "http://216.137.189.57:8080/scrapers/finish/?scrapername=Shannons&auctionnumber=%s&auctionurl=%s&scrapertype=2"%(auctionno, urllib.parse.quote(auctionurl))
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
    pagesneeded=10
    #obj,x22,acname=getitemurls(auctionurl,pagesneeded)
    urllist,catalogTitle,x22=getitemurls(auctionurl,pagesneeded)
    #rint(urllist)
    
    
    
    #print(urllist)
    #getitemdetails(urllist[0])
    
    for v in urllist:
        getitemdetails(v,csvpath,catalogTitle,x22)


    #python shannon.py "https://www.shannons.com/auction-catalog/0122-fine-art-online-auction_U1EN7GVPKV" 2575 C:/Users/Mrugank/Downloads/Selenium/testscrap 1            
#/auction/lot/lot-96---odette-bruneau-french-1891-1984/?lot=432629&so=0&st=&sto=0&au=1011&ef=&et=&ic=False&sd=0&pp=96&pn=1&g=1
