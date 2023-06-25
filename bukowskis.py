from email import header
from json.tool import main
import os
#from tkinter.messagebox import NO
import xlrd
import requests
import urllib
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
#from quantulum3 import parser as qtlum
import unidecode



def getitemurls(mainurl,pageno, headers):
    AuctionInfo={}
    urllist=[]
    r=requests.get(mainurl,headers=headers, allow_redirects=False)
    soup = BeautifulSoup(r.text,'html.parser')
    #print(soup)
    mydivs = soup.find("div", {"class": "c-lot-index__lots"})
    listpaint=mydivs.find_all("div", {"class": "c-lot-index-lot js-market-lot-index-lot js-push-lot-index-lot"})
    for v in listpaint:
        link=v.find("a", {"class": "c-lot-index-lot__link ga-lot-index-lot"})
        urllist.append('https://www.bukowskis.com/'+link['href'])
    return urllist

    
def getitemdetails(mainurl,csvpath):
    AuctionInfo={}
    MainData={}
    htmltagPattern = re.compile("\<\/?[^\<\>]*\/?\>", re.DOTALL)
    MainData["artwork_category"]=''
    #MainData["artcategory"]=''
    MainData["auction_location"]=""
    MainData["auction_num"]=''
    MainData["lot_num"]=''
    MainData["auction_house_name"]="Bukowskis"
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
    mediumPattern = re.compile("(\s+gold)|(silver)|(brass)|(bronze)|(wood)|(porcelain)|(stone)|(marble)|(metal)|(aluminum)|(steel)|(iron)|(copper)|(glass)|(plexiglas)|(chromogenic)|(paper)|(gouache)|(canvas)|(masonite)|(newsprint)|(silkscreen)|(parchment)|(linen)|(inkjet)|(ink\s+jet)|(pigment)|(\stin\s)|(photogravure)|(^oil\s+)|(oil\s+)|(\s+panel\s+)|(terracotta)|(ivory)|(\s+oak\s+)|(^oak\s+)|(\s+oak$)|(alabaster)|(chalk)|(\s+ink\s+)|(ceramic)|(acrylic)|(aluminium)|(aquatint)|(linoleum)|(etching)|(collotype)|(lithograph)|(leather)|(drypoint)|(arches\s+wove)|(pochoir)|(screenprint)|(digital\s+print)|(print\s+in\s+colou?rs)|(Polychrome)|(plastic)|(wool)|(silk)|(cords)|(\s+oak)|(birch)|(pine)|(tuft)|(vinyl)|(velvet)|(textile)|(Lithprint)|(c\-print)|(Pigment)|(lambda\s+print)|(cardboard)|(cibachrome)|(\s+ink)|(etching)|(watercolou?r)", re.DOTALL|re.IGNORECASE)
    #r=requests.get(currenturl, headers=headers,allow_redirects=False)
    matcatdict_en = {}
    matcatdict_fr = {}
    #with open("docs/fineart_materials.csv", newline='') as mapfile:
    with open("/Users/saiswarupsahu/freelanceprojectchetan/docs/fineart_materials.csv", newline='') as mapfile:
            mapreader = csv.reader(mapfile, delimiter=",", quotechar='"')
            for maprow in mapreader:
                matcatdict_en[maprow[1]] = maprow[3]
                matcatdict_fr[maprow[2]] = maprow[3]
    mapfile.close()
    r=requests.get(mainurl,allow_redirects=False)
    MainData["lot_origin_url"]=mainurl
    soup = BeautifulSoup(r.text,'html.parser')
    
    #lotno=soup.find_all("div", {"class": "c-market-lot-show-header__identifiers"})
    #try:
     #   lotno=lotno[0].text
      #  MainData["lot_num"]=lotno
    #except:
     #   lotno = soup.find_all("div", {'class' : 'c-live-lot-show-header__catalogue-number'})
      #  lotno=lotno[0].text
       # MainData["lot_num"]=lotno
    #print(MainData["lot_num"])
    try:
        auctionname=soup.find_all("a", {"class": "c-market-lot-show-navigation__link c-market-lot-show-navigation__link--auction"})
        auctionname=auctionname[0].text
        MainData['auction_name']=auctionname
    except:
        auctionname=soup.find_all("a", {"class": "c-live-lot-show-navigation__link c-live-lot-show-navigation__link--back"})
        auctionname=auctionname[0].text
        MainData['auction_name']=auctionname
    auctionndate=soup.find("div", {"class": "c-market-lot-sidebar__ending"})
    
    description=soup.find_all("div", {"class": "c-market-lot-show-header__title-container"})
    if description is None or description.__len__() == 0:
        description = soup.find_all("div", {"class": "c-live-lot-show-header__title-container"})
    #print(description)
    dates=''
    try:
        dates=description[0].select_one(".c-market-lot-show-header__artist-lifetime")
        if not dates:
            dates = description[0].select_one(".c-live-lot-show-header__artist-lifetime")
        dates=dates.text[dates.text.find("(")+1:dates.text.find(")")]
        dates=dates.split(',')
        MainData["artist_nationality"]=dates[0]
        try:
            MainData["artist_birth"]=dates[1].split('-')[0]
            MainData["artist_birth"] = MainData["artist_birth"].replace("Born ", "")
            MainData["artist_death"]=dates[1].split('-')[1]
        except:
            pass
    except:
        pass

    try:
        MainData["artist_name"]=description[0].find("h1").text
    except:
        pass
    location=soup.find_all("div", {"class": "c-market-lot-show-info__placement"})
    if not location or location.__len__() == 0:
        location = soup.find_all("div", {"class": "c-live-lot-show-info__placement"})
    #MainData['auction_location']=location[0].text.replace('Location:','').strip()
    MainData["auction_location"]="Stockholm"
    auctiondate=soup.find_all("time", {"class": "c-market-lot-show-bidding-end-date"})
    if auctiondate.__len__() > 0:
        x22=parser.parse(auctiondate[0]['datetime'])
        x22=x22.strftime("%d-%b-%y")
        MainData["auction_start_date"]=x22
    estimate=soup.find_all("div", {"class": "c-market-lot-show-estimate__amount"})
    if not estimate or estimate.__len__() == 0:
        estimate = soup.find_all("div", {"class": "c-live-lot-show-info__estimate-ranges"})
    #print(estimate[0].text)
    if estimate.__len__() > 0:
        MainData["price_estimate_max"]=estimate[0].text.strip().encode('ascii', 'ignore').decode("utf-8").replace('SEK','')
        estimateparts = MainData["price_estimate_max"].split("-")
        if estimateparts.__len__() > 1:
            MainData["price_estimate_max"] = estimateparts[1]
            MainData["price_estimate_min"] = estimateparts[0]
    currentbid =soup.find_all("div", {"class": "c-market-lot-show-result"})
    if not currentbid or currentbid.__len__() == 0:
        currentbid = soup.find_all("div", {'class' : 'c-live-lot-show-info__final-price-amount'})
    if(currentbid.__len__() > 0 and currentbid[0].text.find('Contact')==-1):
        #print(currentbid[0].text)
        try:
            MainData["price_sold"]=currentbid[0].find("div",{"class":"c-market-lot-show-result__leading-amount c-market-lot-show-result__leading-amount--reserve-met"}).text.strip().encode('ascii', 'ignore').decode("utf-8") 
            MainData["price_kind"]="price realised"
        except:
            MainData["price_sold"]=currentbid[0].text
            MainData["price_kind"]="price realised"
        if 'price_sold' in MainData.keys() and MainData['price_sold'] != "":
            MainData['price_sold'] = MainData['price_sold'].replace(" ", "")
            MainData['price_sold'] = MainData['price_sold'].replace("SEK", "")
            if 'Currentbid' in MainData["price_sold"]:
                MainData["price_sold"] = ""
                MainData["price_kind"]="estimate"
            else:
                MainData["price_kind"]="price realised"
    else:
        MainData["price_kind"]="estimate"
    #c-market-lot-show-info
    maindesc=soup.find_all("div", {"class": "c-market-lot-show-info"})
    if not maindesc or maindesc.__len__() == 0:
        maindesc = soup.find_all("div", {"class": "c-live-lot-show-info"})
    tesdesc=soup.find_all("p")
    for j in tesdesc:
        aname=re.findall('"([^"]*)"', j.text)
        try:
            MainData["artwork_name"]=aname[0]
        except:
            pass
        
    try:
        aname=re.findall('”([^"]*)"', maindesc[0].text)
        MainData["artwork_name"]=aname[0]
    except:
        pass
    #if 'artwork_name' not in MainData.keys() or MainData["artwork_name"] == "":
    namePattern = re.compile("^(.*?)\,?\s+[\w\s]+\,?\s+\d{4}")
    desctag = soup.find("div", {'class' : 'c-live-lot-show-info__description'})
    if desctag is not None:
        desctext = desctag.renderContents().decode('utf-8')
        nps = re.search(namePattern, desctext)
        if nps:
            MainData["artwork_name"] = nps.groups()[0]
            MainData["artwork_name"] = htmltagPattern.sub("", MainData["artwork_name"])
            #print(MainData["artwork_name"])
    try:
        maindesc=maindesc[0].text.split('.')
    except:
        maindesc = ""
    MainData["artwork_description"]=maindesc 
    listToStr = ' '.join([str(elem) for elem in MainData["artwork_description"]])
    
    MainData["artwork_description"]='<strong><br>Description:</strong><br>'+listToStr
    MainData["artwork_description"]=MainData["artwork_description"].replace('\n','').encode('ascii', 'ignore').decode("utf-8").replace('"','')
    try:
        title=maindesc[0].split(',')
    except:
        title = []
    #df = pd.read_excel('./docs/fineart_materials.xls')
    df = pd.read_excel('/Users/saiswarupsahu/freelanceprojectchetan/docs/fineart_materials.xls')
    mylist1 = df['material_name'].tolist()
    #print(maindesc)
    #print(len(maindesc))
    signedPattern = re.compile("(signed)|(marked)", re.IGNORECASE|re.DOTALL)
    sizePattern = re.compile("(height)|(width)|(diameter)|(depth)", re.IGNORECASE|re.DOTALL)
    sizePattern1 = re.compile("([\d\.]+)\s*x\s*([\d\.]+)\s*x\s*([\d\.]+)\s+(cm)")
    sizePattern2 = re.compile("([\d\.]+)\s*x\s*([\d\.]+)\s+(cm)")
    endcommaPattern = re.compile(",\s*$")
    for x in range(len(maindesc)):
        descparts = maindesc[x].split(",")
        mps = re.search(mediumPattern, maindesc[x])
        #print(maindesc[x])
        if mps and MainData["artwork_materials"] == "":
            MainData["artwork_materials"] = ""
            for descpart in descparts:
                sps = re.search(signedPattern, descpart)
                zps = re.search(sizePattern, descpart)
                if not sps and not zps:
                    MainData["artwork_materials"] += descpart + ","
                elif sps:
                    MainData['artwork_markings'] = descpart
            MainData["artwork_materials"] = endcommaPattern.sub("", MainData["artwork_materials"])
            MainData["artwork_materials"] = MainData["artwork_materials"].replace("\n", "").replace("\r", "")
            MainData["artwork_materials"] = sizePattern1.sub("", MainData["artwork_materials"])
            MainData["artwork_materials"] = sizePattern2.sub("", MainData["artwork_materials"])
            MainData["artwork_markings"] = MainData["artwork_markings"].replace("\n", "").replace("\r", "")
        #print(maindesc[x])
        for t in range(len(mylist1)):
            if(maindesc[x].lower().find(mylist1[t].replace("'","").lower())!=-1):
                MainData["artwork_category"]=df['material_category'][t]
                #MainData["artwork_materials"] = mylist1[t]
        #if(maindesc[x].lower().find("signed")!=-1):
        #    MainData["artwork_markings"]=maindesc[x]
        if(maindesc[x].lower().find("wear")!=-1 or maindesc[x].lower().find("fine")!=-1):
            MainData["artwork_condition_in"]=maindesc[x]
        if(maindesc[x].lower().find(" cm")!=-1 or maindesc[x].lower().find(" inches")!=-1 or maindesc[x].lower().find(" mm")!=-1):        
            #measure=maindesc[x].split('x')
            new_string = ' '.join([w for w in maindesc[x].split() if len(w)<5])
            MainData["artwork_size_notes"]=new_string
            if new_string.find("cm") != -1:
                MainData["auction_measureunit"] = "cm"
                d=new_string.replace('cm','').strip()
                d=d.split('x')
                try:
                    MainData["artwork_measurements_height"]=d[0]
                    MainData["artwork_measurements_width"]=d[1]
                except:
                    pass
            elif(new_string.find("mm")!= -1):
                MainData["auction_measureunit"] = "mm"
                #MainData["auction_measureunit"] = "cm"
                d=new_string.replace('cm','').strip()
                d=d.split('x')
                try:
                    MainData["artwork_measurements_height"]=d[0]
                    MainData["artwork_measurements_width"]=d[1]
                except:
                    pass
            else:
                MainData["auction_measureunit"] = "inches"
               # MainData["auction_measureunit"] = "cm"
                d=new_string.replace('cm','').strip()
                d=d.split('x')
                try:
                    MainData["artwork_measurements_height"]=d[0]
                    MainData["artwork_measurements_width"]=d[1]
                except:
                    pass
    for q in range(len(title)):
        for t in range(len(mylist1)):
            if(title[q].lower().find(mylist1[t].replace("'","").lower())!=-1):
                MainData["artwork_category"]=df['material_category'][t]
                #MainData["artwork_materials"] = title[q].replace('"','')
            if(title[q].lower().find("signed")!=-1):
                MainData["artwork_markings"]=title[q].replace('"','')
        #c-common-lot-show-carousel__link
    if 'artwork_materials' in MainData.keys():
        materials = MainData['artwork_materials']
        materialparts = materials.split(" ")
        catfound = 0
        for matpart in materialparts:
            if matpart in ['in', 'on', 'of', 'the', 'from']:
                continue
            try:
                matPattern = re.compile(matpart, re.IGNORECASE|re.DOTALL)
                for enkey in matcatdict_en.keys():
                    if re.search(matPattern, enkey):
                        MainData['artwork_category'] = matcatdict_en[enkey]
                        catfound = 1
                        break
                for frkey in matcatdict_fr.keys():
                    if re.search(matPattern, frkey):
                        MainData['artwork_category'] = matcatdict_fr[frkey]
                        catfound = 1
                        break
                if catfound:
                    break
            except:
                pass
    imglinks =soup.find_all("a", {"class": "c-common-lot-show-carousel__link"})
    if not imglinks or imglinks.__len__() == 0:
        imglinks = soup.find_all("a", {'class' : 'c-lot-carousel__link'})
    # for u in imglinks:
    #     v=u.find('img')
    #     print(v['src'])
    for uu in range(0,len(imglinks)-1):
        dd="artwork_images"+str(uu+1)
        if(dd=='artwork_images7'):
        	break
        v=imglinks[uu].find('img')        
        MainData[dd]=''
        just=v['src']
        MainData[dd]=just
        #print(imagelist[uu])
    auctionum=MainData["lot_origin_url"]
    #x = re.search(r"/auctions/(.*)?lots", auctionum)
    #print(auctionum)
    result = re.search('/auctions/(.*)/lots', auctionum)
    if result is not None:
        result=result.group(1).replace('/','')
        MainData["auction_num"]=result
    else:
        result = re.search('/auctions/(.*?)/', auctionum)
        result=result.group(1).replace('/','')
        MainData["auction_num"]=result
    #y=re.findall('/auctions/(.*)/lots',mainurl)
    #x=re.findall('/a/(.*)?ic', mainurl) 
    #csvpath=csvpath+"/"+"Bukowskis"+"_"+MainData["auction_num"]+'.csv'
    print(MainData["artwork_materials"])
    keys=["auction_house_name","auction_location","auction_num","auction_start_date","auction_end_date","auction_name","lot_num","sublot_num","price_kind","price_estimate_min","price_estimate_max","price_sold","artist_name","artist_birth","artist_death","artist_nationality","artwork_name","artwork_year_identifier","artwork_start_year","artwork_end_year","artwork_materials","artwork_category","artwork_markings","artwork_edition","artwork_description","artwork_measurements_height","artwork_measurements_width","artwork_measurements_depth","artwork_size_notes","auction_measureunit","artwork_condition_in","artwork_provenance","artwork_exhibited","artwork_literature","artwork_images1","artwork_images2","artwork_images3","artwork_images4","artwork_images5","artwork_images6","image1_name","image2_name","image3_name","image4_name","image5_name","lot_origin_url"]
        
    file_exist=os.path.isfile(csvpath)
    with open(csvpath, 'a', newline='') as output_file:
        keys=["auction_house_name","auction_location","auction_num","auction_start_date","auction_end_date","auction_name","lot_num","sublot_num","price_kind","price_estimate_min","price_estimate_max","price_sold","artist_name","artist_birth","artist_death","artist_nationality","artwork_name","artwork_year_identifier","artwork_start_year","artwork_end_year","artwork_materials","artwork_category","artwork_markings","artwork_edition","artwork_description","artwork_measurements_height","artwork_measurements_width","artwork_measurements_depth","artwork_size_notes","auction_measureunit","artwork_condition_in","artwork_provenance","artwork_exhibited","artwork_literature","artwork_images1","artwork_images2","artwork_images3","artwork_images4","artwork_images5","artwork_images6","image1_name","image2_name","image3_name","image4_name","image5_name","lot_origin_url"]
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
    pageurl = "http://216.137.189.57:8080/scrapers/finish/?scrapername=Bukowski&auctionnumber=%s&auctionurl=%s&scrapertype=2"%(auctionno, urllib.parse.quote(auctionurl))
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
    imagepath = sys.argv[4]
    downloadimages = 0
    convertfractions = 0
    if sys.argv.__len__() > 5:
        downloadimages = sys.argv[5]
    if sys.argv.__len__() > 6:
        convertfractions = sys.argv[6]
    pagesneeded = 15
    file_exist=os.path.isfile(csvpath)
    if file_exist:
        os.unlink(csvpath)
    pagectr = 1
    pageurl = auctionurl
    headers = {'Referer' : auctionurl}
    urllist = []
    while True:
        print(pageurl)
        urllist = getitemurls(pageurl,pagesneeded, headers)
        if urllist.__len__() == 0:
            break
        for o in urllist:
            getitemdetails(o,csvpath)
        headers = {'Referer' : pageurl}
        pagectr += 1
        pageurl = auctionurl + "/page/%s"%pagectr
    updatestatus(auctionnumber, auctionurl)



#Example: python bukowskis.py "https://www.bukowskis.com/en/auctions/F334/lots" F334  /Users/saiswarupsahu/freelanceprojectchetan/buko_F334.csv /home/supmit/work/art2/images/brunk/254 0 0
#https://www.bukowskis.com/en/auctions/E849/lots





