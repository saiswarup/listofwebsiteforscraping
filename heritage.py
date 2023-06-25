# -*- coding: utf-8 -*-
from finefun import *
import subprocess
import os, sys, re, time, gzip
import csv
from tempfile import NamedTemporaryFile
import shutil
import logging
import subprocess
from io import StringIO
#import material_file
#from db import *
from urllib.parse import urlencode, quote_plus
import unidecode


# /// HISTORY/CHANGE LOG -----------------------------------------------------
# DATE            AUTHER                                    ACTION
# 2018-06-19      Saiswarup Sahu <ssahu@artinfo.com>        New version program          Ticket #
emailIdPattern = re.compile(r"\W(\w+\.?\w{0,}@\w+\.\w+\.?\w*)\W", re.MULTILINE | re.DOTALL)
absUrlPattern = re.compile(r"^https?:\/\/", re.IGNORECASE)
anchorTagPattern = re.compile(r"<a\s+[^>]{0,}href=([^\s\>]+)\s?.*?>\s*\w+", re.IGNORECASE | re.MULTILINE | re.DOTALL)
doubleQuotePattern = re.compile('"', re.MULTILINE | re.DOTALL)
htmlTagPattern = re.compile(r"<[^>]+>", re.MULTILINE | re.DOTALL)
newlinePattern = re.compile(r"\n")
multipleWhitespacePattern = re.compile(r"\s+")
pathEndingWithSlashPattern = re.compile(r"\/$")
javascriptUrlPattern = re.compile("^javascript:")
startsWithSlashPattern = re.compile("^/")
htmlEntitiesDict = {'&nbsp;': ' ', '&#160;': ' ', '&amp;': '&', '&#038;': '&', '&lt;': '<', '&#60;': '<', '&gt;': '>',
                    '&#62;': '>', '&apos;': '\'', '&#39;': '\'', '&quot;': '"', '&#34;': '"', '&#8211;': '-',
                    '&euro;': 'Euro', '&hellip;': '...'}


def quoteText(content):
    content = str(stripHtmlEntities(content))
    content = content.replace('"', '\"')
    content = '"' + content + '"'
    return content


def stripHtmlEntities(content):
    for entityKey in htmlEntitiesDict.keys():
        entityKeyPattern = re.compile(entityKey)
        content = re.sub(entityKeyPattern, htmlEntitiesDict[entityKey], content)
    return content


def stripHTML(dataitem):
    dataitem = re.sub(htmlTagPattern, "", dataitem)  # stripped off all HTML tags...
    # Handle HTML entities...
    for entity in htmlEntitiesDict.keys():
        dataitem = dataitem.replace(entity, htmlEntitiesDict[entity])
    return (dataitem)


class Scrape:
    def __init__(self, auctionId, auctionUrl, downloadImages, fp):
        self.auctionId = auctionId
        self.mainUrl = auctionUrl
        self.downloadImages = downloadImages
        self.scrapperName = "Heritage"
        self.fp = fp
        self.httpHeaders = {'Host' : 'fineart.ha.com', 'Cookie' : 's_nr=1642267290241-New; s_cc=true; _g…5D; OptanonAlertBoxClosed=2022-01-15T17:21:30.934Z;'.encode('utf-8')}
        self.run()

    def run(self):
        nextPage = True
        soup = get_soup(self.mainUrl, httpHeaders=self.httpHeaders)
        self.writeHeaders(soup)  # Write the header part of csv
        productDetails = soup.findAll('div', {'class': 'tile-size'})
        print(len(productDetails))
        for product in productDetails:
            auction_house_name = "Heritage"
            auction_location = "Toronto"
            auction_num = ""
            auction_start_date = ""
            auction_end_date = ""
            auction_name=''
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
            artwork_measurements_height = "0"
            artwork_measurements_width = "0"
            artwork_measurements_depth = "0"
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
            aTag = 'https://www.heffel.com/Auction/'+product.find("a")['href']
            try:
                lot_origin_url=aTag
            except:
                pass
            print('_________________________________________________')
            import requests
            from bs4 import BeautifulSoup
            detailPageSoup = aTag
            r = requests.get(detailPageSoup)
            detailPageSoup = BeautifulSoup(r.content,
                                 'html5lib')  # If this line causes an error, run 'pip install html5lib' or install html5lib
            try:
                lot_num=detailPageSoup.find('p',{'class':'lot-details-font-md font-bold'}).find('span').getText()
                print(lot_num)
            except:
                pass
            try:
                artist_name = detailPageSoup.find('div', {'class': 'lot-details-font-lg font-bold'}).getText().strip()
                print(artist_name)
            except:
                pass
            try:
                artist_nationallity=detailPageSoup.find('span', {'id': 'MainContent_artistNationality'}).getText().strip()
                print(artist_nationallity)
            except:
                pass
            try:
                artwork_name=detailPageSoup.find('span', {'id': 'MainContent_itemTitle'}).getText().strip()
                print(artwork_name)
            except:
                pass

            try:
                artwork_materials=detailPageSoup.find('span', {'id': 'MainContent_media'}).getText().strip()
                print(artwork_materials)
            except:
                pass
            try:
                artwork_markings=detailPageSoup.find('span', {'id': 'MainContent_itemInscription'}).getText().strip()
                print(artwork_markings)
            except:
                pass
            try:
                if artwork_edition == '':
                    artwork_edition = getEditionOf(artwork_markings)
            except:
                artwork_edition = ''
                pass
            try:
                years = detailPageSoup.find('span', {'id': 'MainContent_artistDates'}).getText().strip()
                years = re.findall("\d{4}", years)
                artist_birth, artish_death = ['', '']
                if len(years) > 1:
                    artist_birth = years[0]
                    artish_death = years[1]
                elif len(years) == 1:
                    artist_birth = years[0]
            except:
                pass
            try:
                if artwork_measurements_height == '0':
                    dimension = detailPageSoup.find('span', {'id': 'MainContent_dimensionIN'}).getText().strip()
                    auction_measureunit = 'inches'
                    dimaisionList = getDimaision(dimension)
                    artwork_measurements_height = dimaisionList[0]
                    artwork_measurements_width = dimaisionList[1]
                    artwork_measurements_depth = dimaisionList[2]
                    artwork_size_notes = artwork_measurements_height + 'x' + artwork_measurements_width + 'x' + artwork_measurements_depth + " " + 'in'
            except:
                pass
            auction_measureunit = 'in'
            try:
                estimation = detailPageSoup.find('span', {'id': 'MainContent_estimate'}).getText().strip()
                priceList = estimation.replace("Estimate", "").replace(',','').strip().split("-")
                if priceList.__len__() == 2:
                    price_estimate_min = ''.join(re.findall("\d+", X(priceList[0].strip())))
                    price_estimate_max = ''.join(re.findall("\d+", X(priceList[1].strip())))
                if priceList.__len__() == 1:
                   price_estimate_min = ''.join(re.findall("\d+", X(priceList[0].strip())))
                   price_estimate_max = "0"
            except:
                pass
            try:
                priceRealized = detailPageSoup.find('span', {'id': 'MainContent_soldFor'}).getText().strip()
                priceRealized = priceRealized
                price_sold = ''.join(re.findall("\d+", priceRealized.strip()))
            except:
                pass

            if price_estimate_min == '':
                price_estimate_min = '0'
            if price_estimate_max == '':
                price_estimate_max = '0'
            if price_sold == '':
                price_sold = '0'
            if price_sold == "0" and price_estimate_min != "0":
                price_kind = "estimate"
            elif price_sold != "0":
                price_kind = "price realized"
            else:
                price_kind = "unknown"
            try:
                artwork_provenance=detailPageSoup.find('span', {'id': 'MainContent_provenance'}).getText().strip().replace('PROVENANCE','')
                #print(artwork_provenance)
            except:
                pass
            try:
                artwork_literature=detailPageSoup.find('span', {'id': 'MainContent_literature'}).getText().strip().replace('LITERATURE','')
                #print(artwork_literature)
            except:
                pass
            try:
                artwork_description="<strong><br>Description:</strong><br>"+detailPageSoup.find('div', {'id': 'divDescription'}).getText().strip().replace('LITERATURE','<strong><br>Literature:</strong><br>').replace('PROVENANCE','<strong><br>Provenance:</strong><br>')
                #print(artwork_description)
            except:
                pass
            auction_name_details=detailPageSoup.find('div', {'id': 'MainContent_AuctionInfo_divInfo'}).getText(separator=u'@').split('@')
            auction_name=auction_name_details[0]
            try:
                date_data = auction_name_details[-1].split('|')[0].replace(',', '').split(' ')
                date = date_data[2]
                months = date_data[1][0:3]
                year = date_data[-1][-2:]
                if date_data[-1]=='':
                    year = date_data[-2][-2:]
                auction_start_date = date + '-' + months.replace('.', '') + '-' + year
                auction_end_date=date_data[5]+'-'+date_data[4][0:3]+'-'+year
                print(auction_start_date)
            except:
                pass

            try:
                auction_location=detailPageSoup.find('span', {'id': 'MainContent_previewLocation'}).getText(separator=u'@').strip().split('@')[-1].split(' ')[2]
                print(auction_location),'_______'
            except:
                pass


            try:
                artwork_images1 = 'https://www.heffel.com' + \
                                  detailPageSoup.find("img", {"id": "MainContent_bigImage"})['src']
                image1_name = scrapperName+'-'+auction_location+'-'+auction_start_date+'-'+lot_num.strip()+'-'+price_estimate_min+'-a'+'.jpg'
            except:
                pass
            try:
                if artwork_materials.__len__() != 0 or artwork_materials != "":
                    artwork_materials_data = artwork_materials.replace(',', '').split(' ')[0]
                    if artwork_materials_data.lower() == "hanging":
                        artwork_category = "Works on paper"
                    if artwork_materials_data.lower() == "mounted":
                        artwork_category = "Paintings"
                    if artwork_materials_data.lower() == "oil":
                        artwork_category = "Paintings"
                    if artwork_materials_data.lower() == "acrylic":
                        artwork_category = "Paintings"
                    if artwork_materials_data.lower() == "tempera":
                        artwork_category = "Paintings"
                    if artwork_materials_data.lower() == "enamel paint":
                        artwork_category = "Paintings"
                    if artwork_materials_data.lower() == "watercolor":
                        artwork_category = "Works on paper"
                    if artwork_materials_data.lower() == "pencil":
                        artwork_category = "Works on paper"
                    if artwork_materials_data.lower() == "crayon":
                        artwork_category = "Works on paper"
                    if artwork_materials_data.lower() == "pastel":
                        artwork_category = "Works on paper"
                    if artwork_materials_data.lower() == "gouache":
                        artwork_category = "Works on paper"
                    if artwork_materials_data.lower() == "oil pastel":
                        artwork_category = "Works on paper"
                    if artwork_materials_data.lower() == "grease pencil":
                        artwork_category = "Works on paper"
                    if artwork_materials_data.lower() == "ink":
                        artwork_category = "Works on paper"
                    if artwork_materials_data.lower() == "pen":
                        artwork_category = "Works on paper"
                    if artwork_materials_data.lower() == "lithograph":
                        artwork_category = "Prints"
                    if artwork_materials_data.lower() == "screenprint":
                        artwork_category = "Prints"
                    if artwork_materials_data.lower() == "etching":
                        artwork_category = "Prints"
                    if artwork_materials_data.lower() == "engraving":
                        artwork_category = "Prints"
                    if artwork_materials_data.lower() == "woodcut":
                        artwork_category = "Prints"
                    if artwork_materials_data.lower() == "poster":
                        artwork_category = "Prints"
                    if artwork_materials_data.lower() == "linocut":
                        artwork_category = "Prints"
                    if artwork_materials_data.lower() == "monotype":
                        artwork_category = "Prints"
                    if artwork_materials_data.lower() == "c-print":
                        artwork_category = "Photographs"
                    if artwork_materials_data.lower() == "gelatin silver print":
                        artwork_category = "Photographs"
                    if artwork_materials_data.lower() == "platinum":
                        artwork_category = "Photographs"
                    if artwork_materials_data.lower() == "daguerreotype":
                        artwork_category = "Photographs"
                    if artwork_materials_data.lower() == "photogravure":
                        artwork_category = "Photographs"
                    if artwork_materials_data.lower() == "dye transfer print":
                        artwork_category = "Photographs"
                    if artwork_materials_data.lower() == "polaroid":
                        artwork_category = "Photographs"
                    if artwork_materials_data.lower() == "ink-jet":
                        artwork_category = "Photographs"
                    if artwork_materials_data.lower() == "video":
                        artwork_category = "Sculpture"
                    if artwork_materials_data.lower() == "chromogenic":
                        artwork_category = "print"
                    if artwork_materials_data.lower() == "mixed":
                        artwork_category = "Paintings"
                    if artwork_materials_data.lower() == "gelatin":
                        artwork_category = "Photographs"
                    if artwork_materials_data.lower() == "bronze":
                        artwork_category = "Sculptures"
                    if artwork_materials_data.lower() == "sketch":
                        artwork_category = "Works on paper"
                    if artwork_materials_data.lower() == "colored":
                        artwork_category = "Prints"
                    if artwork_materials_data.lower() == "silkscreen":
                        artwork_category = "Prints"
                    if artwork_materials_data.lower() == "serigraph":
                        artwork_category = "Prints"
            except:
                pass

            try:
                if artwork_category == '':
                    artwork_materials_data = artwork_materials.strip().replace('\t', '').split(' ')[0]
                    # print(artwork_materials_data), 'saisidididhdihdihd'
                    if artwork_materials_data.lower() == "hanging":
                        artwork_category = "Works on paper"
                    if artwork_materials_data.lower() == "mounted":
                        artwork_category = "Paintings"
                    if artwork_materials_data.lower() == "oil":
                        artwork_category = "Paintings"
                    if artwork_materials_data.lower() == "acrylic":
                        artwork_category = "Paintings"
                    if artwork_materials_data.lower() == "tempera":
                        artwork_category = "Paintings"
                    if artwork_materials_data.lower() == "enamel paint":
                        artwork_category = "Paintings"
                    if artwork_materials_data.lower() == "watercolor":
                        artwork_category = "Works on paper"
                    if artwork_materials_data.lower() == "pencil":
                        artwork_category = "Works on paper"
                    if artwork_materials_data.lower() == "crayon":
                        artwork_category = "Works on paper"
                    if artwork_materials_data.lower() == "pastel":
                        artwork_category = "Works on paper"
                    if artwork_materials_data.lower() == "gouache":
                        artwork_category = "Works on paper"
                    if artwork_materials_data.lower() == "oil pastel":
                        artwork_category = "Works on paper"
                    if artwork_materials_data.lower() == "grease pencil":
                        artwork_category = "Works on paper"
                    if artwork_materials_data.lower() == "ink":
                        artwork_category = "Works on paper"
                    if artwork_materials_data.lower() == "pen":
                        artwork_category = "Works on paper"
                    if artwork_materials_data.lower() == "lithograph":
                        artwork_category = "Prints"
                    if artwork_materials_data.lower() == "screenprint":
                        artwork_category = "Prints"
                    if artwork_materials_data.lower() == "etching":
                        artwork_category = "Prints"
                    if artwork_materials_data.lower() == "engraving":
                        artwork_category = "Prints"
                    if artwork_materials_data.lower() == "woodcut":
                        artwork_category = "Prints"
                    if artwork_materials_data.lower() == "poster":
                        artwork_category = "Prints"
                    if artwork_materials_data.lower() == "linocut":
                        artwork_category = "Prints"
                    if artwork_materials_data.lower() == "monotype":
                        artwork_category = "Prints"
                    if artwork_materials_data.lower() == "c-print":
                        artwork_category = "Photographs"
                    if artwork_materials_data.lower() == "gelatin silver print":
                        artwork_category = "Photographs"
                    if artwork_materials_data.lower() == "platinum":
                        artwork_category = "Photographs"
                    if artwork_materials_data.lower() == "daguerreotype":
                        artwork_category = "Photographs"
                    if artwork_materials_data.lower() == "photogravure":
                        artwork_category = "Photographs"
                    if artwork_materials_data.lower() == "dye transfer print":
                        artwork_category = "Photographs"
                    if artwork_materials_data.lower() == "polaroid":
                        artwork_category = "Photographs"
                    if artwork_materials_data.lower() == "ink-jet":
                        artwork_category = "Photographs"
                    if artwork_materials_data.lower() == "video":
                        artwork_category = "Sculpture"
                    if artwork_materials_data.lower() == "chromogenic":
                        artwork_category = "print"
                    if artwork_materials_data.lower() == "mixed":
                        artwork_category = "Paintings"
                    if artwork_materials_data.lower() == "gelatin":
                        artwork_category = "Photographs"
                    if artwork_materials_data.lower() == "bronze":
                        artwork_category = "Sculptures"
                    if artwork_materials_data.lower() == "sketch":
                        artwork_category = "Works on paper"
                    if artwork_materials_data.lower() == "colored":
                        artwork_category = "Prints"
                    if artwork_materials_data.lower() == "silkscreen":
                        artwork_category = "Prints"
                    if artwork_materials_data.lower() == "serigraph":
                        artwork_category = "Prints"
            except:
                pass

            try:
                rX = lambda x: " ".join(
                    x.replace(",", "").replace("\n", "").replace("\t", "").replace('"', "").splitlines())
                fp.write(
                    rX(auction_house_name) + ',' + rX(auction_location) + ',' + rX(auction_num) + ',' + rX(
                                        auction_start_date) + ',' + rX(auction_end_date) + ',' + rX(auction_name) + ','
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
                                        image5_name) + ',' + rX(lot_origin_url) + '\n')
            except:
                pass


    def writeHeaders(self, soup):
        auction_name, auction_date, auction_title, auction_location, lotCount, lot_sold_in = "", "", "", "", "", ""
        lot_sold_in = "USD"

        writeHeader(self.fp, auction_name, auction_location, auction_date, auction_title, self.auctionId, lotCount,
                    lot_sold_in)

    def getTextData(self, All_Data, textName):
        try:
            textData = [item for index, item in enumerate(All_Data) if textName in item.lower()][0]
        except:
            return ""

    def getIndexData(self, All_Data, textName):
        try:
            indexNo = [index for index, item in enumerate(All_Data) if textName in item][0]
        except:
            return ""


if __name__ == "__main__":
    if sys.argv.__len__() < 5:
        print("Insufficient parameters")
        sys.exit()
    auctionurl = sys.argv[1]
    auctionnumber = sys.argv[2]
    csvpath = sys.argv[3]
    imagepath = sys.argv[4]
    downloadimages = 0
    if sys.argv.__len__() > 5:
        downloadimages = sys.argv[5]
    #https://fineart.ha.com/c/search-results.zx?N=6413+790+231+4294944949
    fp = open(csvpath, "w")
    Scrape(auctionnumber, auctionurl, downloadimages, fp)
    fp.close()

# Example: python heritage.py https://fineart.ha.com/c/search-results.zx?N=6412+793+794+792+2088+4294943204 6412_793_794_792_2088_4294943204 /home/supmit/work/art2/heritage_6412_793_794_792_2088_4294943204.csv /home/supmit/work/art2/images/heritage/6412_793_794_792_2088_4294943204 0 0
# SaiSwaroop

