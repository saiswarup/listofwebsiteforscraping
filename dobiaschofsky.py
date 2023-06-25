# -*- coding: cp1252 -*-
from finefun import *
import subprocess
import os, sys, re, time, gzip
import csv
from tempfile import NamedTemporaryFile
import shutil
import logging
import subprocess
from io import StringIO
from StringIO import StringIO
import material_file
from db import *
import unidecode

htmlTagPattern = re.compile(r"<[^>]+>", re.MULTILINE | re.DOTALL)
htmlEntitiesDict = {'，':',','&#9313;':'','&#9312;':'','&emsp;':'','&#201;':'e','&nbsp;' : ' ', '&#160;' : ' ', '&amp;' : '&', '&#038;' : '&', '&lt;' : '<', '&#60;' : '<', '&gt;' : '>', '&#62;' : '>', '&apos;' : '\'', '&#39;' : '\'', '&quot;' : '"', '&#34;' : '"', '&#8211;' : '-', '&euro;' : 'Euro' }

httpHeaders = { 'User-Agent' : r'Mozilla/5.0 (X11; Linux i686) AppleWebKit/535.19 (KHTML, like Gecko) Chrome/18.0.1025.162 Safari/535.19',  'Accept' : 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8', 'Accept-Language' : 'en-US,en;q=0.8', 'Accept-Encoding' : 'gzip,deflate,sdch', 'Accept-Charset' : 'ISO-8859-1,utf-8;q=0.7,*;q=0.3', 'Connection' : 'keep-alive'}


def stripHtmlEntities(content):
    for entityKey in htmlEntitiesDict.keys():
        entityKeyPattern = re.compile(entityKey)
        content = re.sub(entityKeyPattern, htmlEntitiesDict[entityKey], content)
    return content
def stripHTML(dataitem):
    dataitem = re.sub(htmlTagPattern, "", dataitem) # stripped off all HTML tags...
    # Handle HTML entities...
    for entity in htmlEntitiesDict.keys():
        dataitem = dataitem.replace(entity, htmlEntitiesDict[entity])
    return(dataitem)


class Scrape:
    def __init__(self,auctionId,mainUrl,domainUrl,downloadImages,scrapperName,fp):
        self.auctionId = auctionId
        self.mainUrl = mainUrl
        self.domainUrl = domainUrl
        self.downloadImages = downloadImages
        self.scrapperName = scrapperName
        self.fp = fp
        self.run()

    def run(self):
        nextPage = True
        soup = get_soup(self.mainUrl)
        self.writeHeaders(soup)#Write the header part of csv
        productDetails = soup.find("div",{"class":"DIV7114treffer"}).findAll("form")
        for product in productDetails:
            auction_house_name = "dobiaschofsky"
            auction_location = ""
            auction_num = ""
            auction_start_date = ""
            auction_end_date = ""
            lot_num = ""
            sublot_num = ""
            price_kind = ""
            price_estimate_min = ""
            price_estimate_max = ""
            price_sold = "0"
            artist_name = ""
            artist_birth = ""
            artish_death = ""
            artist_nationallity = ""
            artwork_name = ""
            artwork_year_identifier = ""
            artwork_start_year = ""
            artwork_end_year = ""
            artwork_materials = ""
            artwork_category = ""
            artwork_markings = ""
            artwork_edition = ""
            artwork_description = ""
            artwork_measurements_height = ""
            artwork_measurements_width = ""
            artwork_measurements_depth = ""
            artwork_size_notes = ""
            auction_measureunit = ""
            artwork_condition_in = ""
            artwork_provenance = ""
            artwork_exhibited = ""
            artwork_literature = ""
            artwork_images1 = ""
            artwork_images2 = ""
            artwork_images3 = ""
            artwork_images4 = ""
            artwork_images5 = ""
            image1_name = ""
            image2_name = ""
            image3_name = ""
            image4_name = ""
            image5_name = ""
            lot_origin_url = ""
            aTag = product['action']
            print (aTag),'jfhafjha'
            detailPageUrl = self.domainUrl+aTag
            detailPageUrl=detailPageUrl.replace("https","http")
            lot_origin_url=detailPageUrl.replace('"', '')

            auction_num=auctionId
            try:
                detailPageSoup = get_soup(detailPageUrl)
            except:
                pass
            try:
                detailPageList = detailPageSoup.find("div",{"class": "DIV7111left"})#.getText()
                #print ("<strong><br>Description:</strong><br>"+detailPageList.getText(separator=u' ').replace("\n",''))
            except:
                pass
            try:
                lot_num_data = detailPageList.find("h1").getText().split("\n") # .getText().strip()
                if lot_num_data.__len__() == 2:
                    lot_num = X(lot_num_data[0].strip()).replace("€","").strip()
                    artist_name = X(lot_num_data[1].strip()).replace("€","").strip()
                if lot_num_data.__len__() == 1:
                    lot_num = X(lot_num_data[0].strip()).replace("€","").strip()
                    artist_name = "0"
            except:
                pass
            print(lot_num)
            try:
                year_list = detailPageList.getText(separator=u'@').split("@")[2]
                year_list = re.findall('\d\d\d\d', year_list)
                if year_list.__len__() == 2:
                    artist_birth = X(year_list[0].strip()).replace("€", "").strip()
                    artish_death = X(year_list[1].strip()).replace("€", "").strip()
                if year_list.__len__() == 1:
                    artist_birth = X(year_list[0].strip()).replace("€", "").strip()
                    artish_death = ""
            except:
                pass
            try:
                artwork_name=detailPageList.find_all('p')[0].getText()
            except:
                pass

            try:
                dimPartList = [x for x in detailPageList.getText(separator=u'@').split("@") if " cm" in x]
                if dimPartList.__len__() == 1 or dimPartList.__len__() > 1:
                    dimaisionList = getDimaision(dimPartList[0].replace(',', '.'))
                    artwork_measurements_height = dimaisionList[0]
                    artwork_measurements_width = dimaisionList[1]
                    artwork_measurements_depth = dimaisionList[2]
                    artwork_size_notes = artwork_measurements_height + 'x' + artwork_measurements_width + 'x' + artwork_measurements_depth
                    auction_measureunit = "cm"
            except:
                pass
            try:
                artwork_materials = detailPageList.find_all('p')[1].getText(separator=u'@').split("@")[0].replace(',','')
            except:
                pass
            pricelist=detailPageList.find("form",{"name":"gebotform"}).findAll("td",{"style":"text-align:right"})#[-1].getText()
            try:
                price_sold = detailPageList.find("form", {"name": "gebotform"}).find("td",{"style":"color:#004e6c;text-align:right;padding-top:5px"}).getText()
                print (price_sold)
            except:
                pass
            if pricelist.__len__() == 3:
                price_estimate_min = X(pricelist[0].getText().strip()).replace("€", "").strip()
                price_estimate_max = "0"
            try:
                price_sold=''.join(re.findall("\d",price_sold))
                price_estimate_min=''.join(re.findall("\d",price_estimate_min))
            except:
                pass

            if price_sold != "0":
                price_kind = "price realized"
            elif price_estimate_min != '0' or price_estimate_max != '0':
                price_kind = 'estimate'
            else:
                price_kind = "unknown"
            artwork_images=detailPageSoup.find("div",{"class": "DIV7111right"}).findAll('img',{"title":"Click to enlarge"})
            try:
                artwork_images1="https://www.dobiaschofsky.com"+artwork_images[0]['src']
                image1_name = scrapperName+'_'+lot_num+'_'+artwork_images1.split('/')[-1]
            except:
                pass
            try:
                artwork_images2="https://www.dobiaschofsky.com"+artwork_images[1]['src'].replace("/70/","/3000/")
                image2_name = scrapperName+'_'+lot_num+'_'+artwork_images2.split('/')[-1]
            except:
                pass
            try:
                artwork_images3="https://www.dobiaschofsky.com"+artwork_images[2]['src'].replace("/70/","/3000/")
                image3_name = scrapperName+'_'+lot_num+'_'+artwork_images3.split('/')[-1]
            except:
                pass
            try:
                artwork_images4="https://www.dobiaschofsky.com"+artwork_images[3]['src'].replace("/70/","/3000/")
                image4_name = scrapperName+'_'+lot_num+'_'+artwork_images4.split('/')[-1]
            except:
                pass
            try:
                artwork_images5="https://www.dobiaschofsky.com"+artwork_images[4]['src'].replace("/70/","/3000/")
                image5_name = scrapperName+'_'+lot_num+'_'+artwork_images5.split('/')[-1]
            except:
                pass
            timeing=detailPageSoup.find("div",{"class":"DIV7111left"}).getText(separator=u'@').split("@")
            time_zone=[x for x in timeing if "Sale time:" in x]
            if time_zone.__len__() == 1:
                time_zone=time_zone[0].split(":")[-1]
                print(time_zone.split('.'))
                if time_zone.split('.')[1]=="1":
                    month='Jan'
                if time_zone.split('.')[1]=="2":
                    month='Feb'
                if time_zone.split('.')[1]=="3":
                    month='Mar'
                if time_zone.split('.')[1]=="4":
                    month='Apr'
                if time_zone.split('.')[1]=="5":
                    month='May'
                if time_zone.split('.')[1]=="6":
                    month='Jun'
                if time_zone.split('.')[1]=="7":
                    month='Jul'
                if time_zone.split('.')[1]=="8":
                    month='Aug'
                if time_zone.split('.')[1]=="9":
                    month='Sep'
                if time_zone.split('.')[1]=="10":
                    month='Oct'
                if time_zone.split('.')[1]=="11":
                    month='Nov'
                if time_zone.split('.')[1]=="12":
                    month='Dec'
            auction_start_date=time_zone.split('.')[0]+'-'+month+'-'+time_zone.split('.')[-1]
            artwork_description="<strong><br>Description:</strong><br>"+detailPageList.getText(separator=u' ').replace("\n",'')
            auction_location='Bern'
            lot_origin_url=''.join(c for c in lot_origin_url if c not in '"')
            rX = lambda x: " ".join(x.replace(",", "").replace("\n", "").replace("\t", "").replace('"', "").splitlines())
            fp.write(
                rX(auction_house_name) + ',' + rX(auction_location) + ',' + rX(auction_num) + ',' + rX(
                    auction_start_date) + ',' + rX(auction_end_date) + ','
                + rX(lot_num) + ',' + rX(sublot_num) + ',' + rX(price_kind) + ',' + rX(
                    price_estimate_min) + ',' + rX(price_estimate_max) + ',' + rX(price_sold) + ',' + rX(
                    artist_name) + ','
                + rX(artist_birth) + ',' + rX(artish_death) + ',' + rX(artist_nationallity) + ',' + rX(
                    artwork_name) + ',' +
                rX(artwork_year_identifier) + ',' + rX(artwork_start_year) + ',' + rX(
                    artwork_end_year) + ',' + rX(
                    artwork_materials) + ',' + rX(artwork_category) + ',' + rX(artwork_markings) + ','
                + rX(artwork_edition) + ',' + rX(artwork_description) + ',' + rX(
                    artwork_measurements_height) + ',' + rX(artwork_measurements_width) + ',' + rX(
                    artwork_measurements_depth) + ',' +
                rX(artwork_size_notes) + ',' + rX(auction_measureunit) + ',' + rX(
                    artwork_condition_in) + ',' + rX(
                    artwork_provenance) + ',' + rX(artwork_exhibited) + ',' + rX(artwork_literature) + ',' +
                rX(artwork_images1) + ',' + rX(artwork_images2) + ',' + rX(artwork_images3) + ',' + rX(
                    artwork_images4) + ',' + rX(artwork_images5) + ',' +
                rX(image1_name) + ',' + rX(image2_name) + ',' + rX(image3_name) + ',' + rX(
                    image4_name) + ',' + rX(
                    image5_name) + ',' + rX(lot_origin_url) + '"\n')



    def writeHeaders(self,soup):
        auction_name, auction_date, auction_title, auction_location, lotCount, lot_sold_in = "", "", "", "", "", ""
        lot_sold_in = "EUR"
        auction_name = "Ader"
        auction_location=''
        try:
            auction_location = soup.find("div", {'class': 'lieu_vente'}).getText().replace(',', ' ')
        except:
            pass
        try:
            auction_title = soup.find("h1",{"class": "nom_vente"}).getText().replace("|","")
        except:
            pass
        try:
            auction_date=soup.findAll('div',{'class':'date_vente'})[0].getText().encode('utf8').strip()
            dateFormat=re.search(r".*(\s\d+)\s(.*)\s(\d{4}).*",auction_date)
            if dateFormat:
                month=dateFormat.group(2)
                monthDict ={"janvier": "January","f\E9vrier": "February","mars": "March","avril": "April","mai": "May","juin": "June","juillet": "July","ao\FBt": "August","septembre": "September","octobre": "October","novembre": "November","d\E9cembre": "December"}
                for entityKey in monthDict.keys():
                                        entityKeyPattern = re.compile(entityKey)
                                        month = re.sub(entityKeyPattern, monthDict[entityKey], month)
            auction_date=dateFormat.group(1)+" "+month+" "+ dateFormat.group(3)
        except:
            pass
        try:
            lotCount=soup.findAll('div',{'class':'nbre_lot_haut'})[0].getText().encode('utf8').strip()
            lotCount=''.join(re.findall('sur(.*)',lotCount)).strip()
        except:
            pass

        #print "lotCount: ", lotCount, "date: ", auction_date, "Title: ", auction_title, "AuctionLocation: ", auction_location
        writeHeader(self.fp,auction_name,auction_location,auction_date,auction_title,auctionId,lotCount,lot_sold_in)

    def getTextData(self,detailPageList,textName):
        try:
            textData = [item for index,item in enumerate(detailPageList) if textName in item.lower()][0]
            provenance = textData.strip().replace("\n","").replace("\r","").replace(">","")
            return provenance
        except:
            return ""

    def getIndexData(self,detailPageList,textName):
        try:
            indexNo = [index for index,item in enumerate(detailPageList) if textName in item][0]
            provenance = textName +" " + detailPageList[indexNo+1]
            provenance = provenance.strip().replace("\n","").replace("\r","")
            return provenance
        except:
            return ""

if __name__ == "__main__":
    auctionId = sys.argv[1]
    mainUrl = "https://www.dobiaschofsky.com/" + auctionId+".html?setn=300"
    domainUrl = "https://www.dobiaschofsky.com"
    scrapperName = "dobiaschofsky"
    downloadImages = False
    if sys.argv.__len__() > 2 and sys.argv[2] == "True":
        downloadImages = "True"

    # imageDir = createImageDir(scrapperName,auctionId)
    datafile = getDataFilename(scrapperName, auctionId)
    fp = open(datafile, "w")

    Scrape(auctionId, mainUrl, domainUrl, downloadImages, scrapperName, fp)
    fp.close()
