# -*- coding: utf-8 -*-
from finefun import *
import subprocess
import os, sys, re, time, gzip
from tempfile import NamedTemporaryFile
import shutil
import logging
import subprocess
import io
#import material_file
#from db import *
import sys
import csv
from datetime import datetime
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
    def __init__(self, auctionId, mainUrl, downloadImages, imagepath, fp):
        self.auctionId = auctionId
        self.mainUrl = mainUrl
        self.domainUrl = "https://www.skinnerinc.com"
        self.downloadImages = downloadImages
        self.scrapperName = "Skinner"
        self.imagepath = imagepath
        self.fp = fp
        soup = get_soup(self.mainUrl)
        pagecontent = requests.get(self.mainUrl).text
        self.soup = soup
        self.writeHeaders(soup)  # Write the header part of csv
        pagectr = 1
        beginspacePattern = re.compile("^\s+")
        endspacePattern = re.compile("\s+$")
        lotsPattern = re.compile("Lots\s+\d+\s+\-\s+\d+")
        absurlPattern = re.compile("^https?:\/\/", re.IGNORECASE)
        lotlistPattern = re.compile("\"lots\"\:\{\"result_page\"\:(\[.*\"\}\}\}\])")
        llps = re.search(lotlistPattern, pagecontent)
        lotslist = []
        if llps:
            lotslistjson = llps.groups()[0]
            lotslist = json.loads(lotslistjson)
            #print(lotslist[0]['_jsonld'])
        while True:
            self.run(soup)
            pagectr += 1
            alllotsanchortags = soup.find_all("a", {'title' : lotsPattern})
            if alllotsanchortags.__len__() == 0:
                #print(lotslist.__len__())
                #print("Page: %s"%pagectr)
                self.getdatafromjson(lotslist)
                # Get next page here...
                nextpageurl = self.mainUrl + "?page=%s&limit=36"%pagectr
                nextpagecontent = requests.get(nextpageurl).text
                llps = re.search(lotlistPattern, nextpagecontent)
                lotslist = []
                if llps:
                    lotslistjson = llps.groups()[0]
                    lotslist = json.loads(lotslistjson)
                if lotslist.__len__() == 0:
                    break
                continue
            #print(alllotsanchortags.__len__())
            foundflag = False
            nextpageurl = ""
            for lotanchor in alllotsanchortags:
                anchorcontents = lotanchor.renderContents().decode('utf-8')
                anchorcontents = anchorcontents.replace("\n", "").replace("\r", "")
                anchorcontents = beginspacePattern.sub("", anchorcontents)
                anchorcontents = endspacePattern.sub("", anchorcontents)
                if str(pagectr) == anchorcontents:
                    nextpageurl = lotanchor['href']
                    if not re.search(absurlPattern, nextpageurl):
                        nextpageurl = self.domainUrl + nextpageurl
                    foundflag = True
                    break
            if not foundflag:
                break
            soup = get_soup(nextpageurl)
            self.soup = soup

    def run(self, soup):
        matcatdict_en = {}
        matcatdict_fr = {}
        with open("/root/artwork/deploydirnew/docs/fineart_materials.csv", newline='') as mapfile:
        #with open("docs/fineart_materials.csv", newline='') as mapfile:
            mapreader = csv.reader(mapfile, delimiter=",", quotechar='"')
            for maprow in mapreader:
                matcatdict_en[maprow[1]] = maprow[3]
                matcatdict_fr[maprow[2]] = maprow[3]
        mapfile.close()
        titlePattern = re.compile("([^\(]+)\s*\(([^,]+),\s+(\d{4})\-?(\d{0,4})")
        productDetails = soup.findAll('ul', {'class': 'auction-button-list'})
        for product in productDetails:
            auction_house_name = "Skinner"
            auction_location = ""
            auction_num = ""
            auction_start_date = ""
            auction_end_date = ""
            auction_name = ''
            lot_num = ""
            sublot_num = ""
            price_kind = ""
            price_estimate_min = ""
            price_estimate_max = ""
            price_sold = ""
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
            try:
                aTag = product.find("a")
                #print(aTag)
            except:
                aTag = None
                pass
            titletags = soup.find_all("title")
            if titletags.__len__() > 0:
                titlecontents = titletags[0].renderContents().decode('utf-8')
                titleparts = titlecontents.split("|")
                if titleparts.__len__() > 0:
                    auction_name = titleparts[0]
            locationspantags = soup.find_all("span", {'itemprop' : 'addressRegion'})
            if locationspantags.__len__() > 0:
                locationcontents = locationspantags[0].renderContents().decode('utf-8')
                auction_location = locationcontents
            if aTag:
                detailPageUrl = aTag["href"]
                try:
                    lot_origin_url=detailPageUrl
                    print(lot_origin_url)
                except:
                    pass
                print("Getting '%s'..."%detailPageUrl)
                detailPageSoup = get_soup(detailPageUrl)
                try:
                    lot_num = detailPageSoup.find('div', {'class', 'lot-title'}).find('span').getText()
                except:
                    pass
                try:
                    lot_num,sublot_num=getSubLot(lot_num)
                except:
                    pass
                try:
                    All_Data = detailPageSoup.find('section', {'id': 'overview'}).find('p').getText(separator=u'@').strip().replace('@@@', '@').replace('@@', '@').split("@")
                    #print(detailPageSoup.find('section', {'id': 'overview'}).find('p').getText())
                except:
                    pass
                try:
                    if "(" in All_Data[0]:
                        artist_name = All_Data[0]
                        artwork_name = All_Data[4]
                    if artist_name=='':
                        artist_name = All_Data[0]
                    if artwork_name=='':
                        artwork_name = All_Data[4]
                    try:
                        artist_birth, artish_death = getStartEndYear(artist_name)
                    except:
                        pass

                    try:
                        if '-' in artist_name:
                            artist_nationallity = artist_name.split('-')[0]
                            artist_nationallity = re.sub(".*['(']", '', artist_nationallity)
                            artist_nationallity = ''.join(re.findall("[A-Za-z].*?\s", artist_nationallity))
                        artist_name = re.sub("['('].*", '', artist_name)
                    except:
                        pass
                except:
                    pass
                beginspacePattern = re.compile("^\s+")
                artwork_name_lot=detailPageSoup.find('div', {'class', 'lot-title'}).find('h1').getText()
                #artwork_name=''.join(re.findall("[')'].*",artwork_name_lot))
                artwork_name=artwork_name_lot
                artwork_name=artwork_name.replace(")","")

                if "," in artwork_name_lot:
                    artwork_name=artwork_name_lot.split(",")[-1]
                if ")" in artwork_name:
                    artwork_name=artwork_name.split(")")[-1]
                try:
                    if artwork_name=='':
                        artwork_name = All_Data[4]
                except:
                    pass

                if All_Data[2]=="" and artwork_name=='':
                    artwork_name=All_Data[4]
                elif artwork_name=='':
                    artwork_name=All_Data[2].encode('utf-8').strip()
                artwork_name = str(artwork_name)
                artwork_name = beginspacePattern.sub("", artwork_name)
                artwork_name = artwork_name.replace('"', "")
                try:
                    if artwork_name=='':
                        artwork_name = All_Data[1].encode('ascii', 'ignore').decode('ascii')
                        #print(artwork_name), "7y7y7y7y7yy"
                except:
                    pass
                try:
                    artwork_start_year, artwork_end_year = getStartEndYear(artwork_name)
                except:
                    pass
                try:
                    artwork_markings_data=[x for x in All_Data if "Signed" in x.strip() or "unsigned" in x.lower()][0].strip().replace(".,",'-').replace(',','-').replace('.','-').split('-')
                    #print(artwork_markings_data),'===================='
                    if artwork_markings=='':
                        artwork_markings = getSignature(artwork_markings_data)
                       # print(artwork_markings)
                    if artwork_markings=='':
                        artwork_markings = getSignature(detailPageSoup.find('section', {'id': 'overview'}).find('p').getText().replace(",",".").split('.'))
                except:
                    pass
                if ";" in artwork_markings:
                    artwork_markings=artwork_markings.split(';')[0]
                try:
                    # if artwork_materials=='':
                    #     artwork_materials = getMaterial(artwork_markings_data)
                    if artwork_materials=='':
                        artwork_materials = getMaterial(detailPageSoup.find('section', {'id': 'overview'}).find('p').getText().replace(",",".").split('.'))

                except:
                    pass
                try:
                    artwork_condition_in = [x for x in All_Data if "Condition" in x.strip()][0].strip()
                    artwork_condition_in=''.join(re.findall("Condition:.*",artwork_condition_in))
                except:
                    pass
                try:
                    artwork_provenance = [x for x in All_Data if "provenance" in x.lower().strip()][0].strip()
                except:
                    pass
                try:
                    artwork_exhibited = [x for x in All_Data if "exhibitions" in x.lower().strip()][0].strip()
                except:
                    pass
                try:
                    artwork_edition = [x for x in All_Data if "numbered" in x.lower().strip()][0].strip()
                    artwork_edition = ''.join(re.findall('numbered \'?(\d+\/\d+)\'?.*', artwork_edition))
                    artwork_edition = artwork_edition.replace('/', ' of ')
                except:
                    pass
                try:
                    h3tags = detailPageSoup.find_all("h3")
                    sizePattern1 = re.compile("([\d\s\.\/x]+)\s+(in)\.?")
                    sizePattern2 = re.compile("([\d\s\.\/x]+)\s+(cm)\.?")
                    if h3tags.__len__() > 0:
                        ptag = h3tags[0].findNext("p")
                        if ptag is not None:
                            pcontents = ptag.renderContents().decode('utf-8')
                            zps1 = re.search(sizePattern1, pcontents)
                            zps2 = re.search(sizePattern2, pcontents)
                            if zps1:
                                size = zps1.groups()[0]
                                sizeparts = size.split("x")
                                artwork_measurements_height = sizeparts[0]
                                artwork_measurements_width = beginspacePattern.sub("", sizeparts[1])
                                if sizeparts.__len__() > 2:
                                    artwork_measurements_depth = beginspacePattern.sub("", sizeparts[2])
                                auction_measureunit = zps1.groups()[1]
                            elif zps2:
                                size = zps2.groups()[0]
                                sizeparts = size.split("x")
                                artwork_measurements_height = sizeparts[0]
                                artwork_measurements_width = beginspacePattern.sub("", sizeparts[1])
                                if sizeparts.__len__() > 2:
                                    artwork_measurements_depth = beginspacePattern.sub("", sizeparts[2])
                                auction_measureunit = zps2.groups()[1]
                            artwork_size_notes = artwork_measurements_height + 'x' + artwork_measurements_width + 'x' + artwork_measurements_depth + " " + auction_measureunit
                except:
                    pass
                #print(artwork_size_notes + "+++++++++++++++++++++++++++")
                if artwork_measurements_height=='0':
                    try:
                        dimension = [x for x in All_Data if  " in.," in x.strip()]
                        #print(dimension), '+++++++++++++++++++++++++++++'
                        dimension = dimension[0]
                        dimension = ''.join(re.findall(",\s.*\sin.,", dimension))
                        dimension1=dimension.split(',')
                        #print(dimension1)
                        dimension = [x for x in dimension1 if " in." in x.strip()][0].replace("in.","")
                        print(dimension)
                        auction_measureunit = 'in'
                        size = dimension.replace('&nbsp;', ' ').strip()
                        dimaisionList = getDimaision(dimension)
                        artwork_measurements_height = dimaisionList[0]
                        artwork_measurements_width = dimaisionList[1]
                        artwork_measurements_depth = dimaisionList[2]
                        artwork_size_notes = artwork_measurements_height + 'x' + artwork_measurements_width + 'x' + artwork_measurements_depth + " " + 'in'
                    except:
                        pass

                try:
                    if len(All_Data) > 1:
                        estimation = [x for x in All_Data if "Estimate" in x.strip()]
                        if estimation.__len__() != 0:
                            estimation = estimation[0]
                            priceList = estimation.replace("Estimate", "").strip().split("-")
                            if priceList.__len__() == 2:
                                price_estimate_min = ''.join(re.findall("\d+", X(priceList[0].strip())))
                                price_estimate_max = ''.join(re.findall("\d+", X(priceList[1].strip())))
                            if priceList.__len__() == 1:
                                price_estimate_min = ''.join(re.findall("\d+", X(priceList[0].strip())))
                                price_estimate_max = "0"
                except:
                    pass
                try:
                    priceRealized = detailPageSoup.find('div', {'class', 'item-description-estimate'}).find("span",{"class":"fullprice"}).getText()
                    #print(priceRealized)
                    price_sold = ''.join(re.findall("\d+", priceRealized.strip()))
                    #print(price_sold)
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
                auction_num=self.auctionId
                try:
                    artwork_description = "<strong><br>Description:</strong><br>" + '  ' + lot_num + '  ' + detailPageSoup.find('section', {'id': 'overview'}).find('p').getText(' ').strip()
                    artwork_description = artwork_description.replace('Provenance','<Strong><br>Provenance</strong><br>').replace('Exhibitions','<Strong><br>Exhibitions</strong><br>')
                except:
                    pass
                try:
                    image_details = detailPageSoup.find("div", {'class', 'app-figure zoom-gallery'}).find('a')
                    artwork_images1 = image_details['href']
                    #image1_name = scrapperName + '-' + auction_start_date + '-' + self.auctionId + '-' + lot_num + '-' + price_estimate_min + '-a' + '.jpg'
                    processedArtistName = artist_name.replace(" ", "_")
                    processedArtistName = unidecode.unidecode(processedArtistName)
                    image1_name = self.auctionId + "__" + processedArtistName + "__" + str(lot_num) + "_a.jpg"
                except:
                    pass
                if artwork_images2=='':
                    try:
                        images = detailPageSoup.find("div", {'class', 'selectors MagicScroll'}).findAll('a')
                        artwork_images2 = images[1]['href']
                        #image2_name = scrapperName + '-' + auction_start_date + '-' + self.auctionId + '-' + lot_num + '-' + price_estimate_min + '-b' + '.jpg'
                        processedArtistName = artist_name.replace(" ", "_")
                        processedArtistName = unidecode.unidecode(processedArtistName)
                        image2_name = self.auctionId + "__" + processedArtistName + "__" + str(lot_num) + "_b.jpg"
                        image2_name = image2_name.replace('_', '-')
                    except:
                        pass

                if artwork_images3=='':
                    try:
                        images = detailPageSoup.find("div", {'class', 'selectors MagicScroll'}).findAll('a')
                        artwork_images3 = images[2]['href']
                        #image3_name = scrapperName + '-' + auction_start_date + '-' + self.auctionId + '-' + lot_num + '-' + price_estimate_min + '-c' + '.jpg'
                        processedArtistName = artist_name.replace(" ", "_")
                        processedArtistName = unidecode.unidecode(processedArtistName)
                        image3_name = self.auctionId + "__" + processedArtistName + "__" + str(lot_num) + "_c.jpg"
                        image3_name = image3_name.replace('_', '-')
                    except:
                        pass
                if artwork_images4=='':
                    try:
                        images = detailPageSoup.find("div", {'class', 'selectors MagicScroll'}).findAll('a')
                        artwork_images4 = images[3]['href']
                        #image4_name = scrapperName + '-' + auction_start_date + '-' + self.auctionId + '-' + lot_num + '-' + price_estimate_min + '-d' + '.jpg'
                        processedArtistName = artist_name.replace(" ", "_")
                        processedArtistName = unidecode.unidecode(processedArtistName)
                        image4_name = self.auctionId + "__" + processedArtistName + "__" + str(lot_num) + "_d.jpg"
                        image4_name = image4_name.replace('_', '-')
                    except:
                        pass
                if artwork_images5=='':
                    try:
                        images = detailPageSoup.find("div", {'class', 'selectors MagicScroll'}).findAll('a')
                        artwork_images5 = images[4]['href']
                        #image5_name = scrapperName + '-' + auction_start_date + '-' + self.auctionId + '-' + lot_num + '-' + price_estimate_min + '-e' + '.jpg'
                        processedArtistName = artist_name.replace(" ", "_")
                        processedArtistName = unidecode.unidecode(processedArtistName)
                        image5_name = self.auctionId + "__" + processedArtistName + "__" + str(lot_num) + "_e.jpg"
                        image5_name = image5_name.replace('_', '-')
                    except:
                        pass
                # if artwork_images1=='':
                #     image_details=detailPageSoup.find("div", {'class', 'app-figure zoom-gallery'}).find('a')
                #     artwork_images1 = image_details['href']
                #     image1_name = scrapperName + '-' + auction_start_date + '-' + self.auctionId + '-' + lot_num + '-' + price_estimate_min + '-a' + '.jpg'
                # else:
                #     pass
                artwork_materials=re.sub("^[a-z].*","",artwork_materials.strip())
                artwork_materials = re.sub("^\s[a-z].*", "", artwork_materials.strip())
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
                        if artwork_materials_data.lower() == "huile":
                            artwork_category = "Paintings"
                        if artwork_materials_data.lower() == "technique":
                            artwork_category = "Paintings"
                        if artwork_materials_data.lower() == "toile":
                            artwork_category = "Paintings"
                        if artwork_materials_data.lower() == "color":
                            artwork_category = "Prints"
                except:
                    pass
                try:
                    if artwork_category == '':
                        artwork_materials_data = artwork_materials.strip().replace('\t', '').split(' ')[0]
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
                        if artwork_materials_data.lower() == "huile":
                            artwork_category = "Paintings"
                        if artwork_materials_data.lower() == "color":
                            artwork_category = "Prints"
                except:
                    pass
                # auction_start_date='11-Jan-21'
                # auction_end_date='21-Jan-21'
                # auction_name='Fine Paintings & Sculpture'

                auction_start_date1=soup.find("span",{"itemprop":"startDate"}).getText()
                if auction_start_date1.split("-")[0]=='11':
                    month='Nov'
                if auction_start_date1.split("-")[0]=='01':
                    month='Jan'
                if auction_start_date1.split("-")[0]=='02':
                    month='Feb'
                if auction_start_date1.split("-")[0] == '03':
                    month = 'Mar'
                if auction_start_date1.split("-")[0] == '04':
                    month = 'Apr'
                if auction_start_date1.split("-")[0] == '05':
                    month = 'May'
                if auction_start_date1.split("-")[0] == '06':
                    month = 'Jun'
                if auction_start_date1.split("-")[0] == '07':
                    month = 'Jul'
                if auction_start_date1.split("-")[0] == '08':
                    month = 'Aug'
                if auction_start_date1.split("-")[0] == '09':
                    month = 'Sep'
                if auction_start_date1.split("-")[0] == '10':
                    month = 'Oct'
                if auction_start_date1.split("-")[0] == '12':
                    month = 'Dec'
                auction_start_date=auction_start_date1.split("-")[1]+'-'+month+'-'+auction_start_date1.split("-")[-1][-2:]

                auction_end_date1 = soup.find("span", {"itemprop": "endDate"}).getText()
                if auction_end_date1.split("-")[0]=='11':
                    month='Nov'
                if auction_end_date1.split("-")[0]=='01':
                    month='Jan'
                if auction_end_date1.split("-")[0]=='02':
                    month='Feb'
                if auction_end_date1.split("-")[0] == '03':
                    month = 'Mar'
                if auction_end_date1.split("-")[0] == '04':
                    month = 'Apr'
                if auction_end_date1.split("-")[0] == '05':
                    month = 'May'
                if auction_end_date1.split("-")[0] == '06':
                    month = 'Jun'
                if auction_end_date1.split("-")[0] == '07':
                    month = 'Jul'
                if auction_end_date1.split("-")[0] == '08':
                    month = 'Aug'
                if auction_end_date1.split("-")[0] == '09':
                    month = 'Sep'
                if auction_end_date1.split("-")[0] == '10':
                    month = 'Oct'
                if auction_end_date1.split("-")[0] == '12':
                    month = 'Dec'
                auction_end_date=auction_end_date1.split("-")[1]+'-'+month+'-'+auction_end_date1.split("-")[-1][-2:]
                auction_location = str(auction_location)
                auction_num = str(auction_num)
                auction_start_date = str(auction_start_date)
                auction_end_date = str(auction_end_date)
                auction_name = str(auction_name)
                lot_num = str(lot_num)
                price_kind = str(price_kind)
                price_estimate_min = str(price_estimate_min)
                price_estimate_max = str(price_estimate_max)
                price_sold = str(price_sold)
                artist_name = str(artist_name)
                artist_birth = str(artist_birth)
                artish_death = str(artish_death)
                artist_nationallity = str(artist_nationallity)
                artwork_name = str(artwork_name)
                artwork_year_identifier = str(artwork_year_identifier)
                artwork_start_year = str(artwork_start_year)
                artwork_end_year = str(artwork_end_year)
                artwork_materials = str(artwork_materials)
                artwork_category = str(artwork_category)
                artwork_markings = str(artwork_markings)
                artwork_edition = str(artwork_edition)
                artwork_description = str(artwork_description)
                artwork_description = artwork_description.replace(";", "")
                artwork_measurements_height = str(artwork_measurements_height)
                artwork_measurements_width = str(artwork_measurements_width)
                artwork_measurements_depth = str(artwork_measurements_depth)
                artwork_size_notes = str(artwork_size_notes)
                auction_measureunit = str(auction_measureunit)
                artwork_condition_in = str(artwork_condition_in)
                artwork_provenance = str(artwork_provenance.replace("Provenance:", "").strip())
                artwork_exhibited = str(artwork_exhibited)
                artwork_literature = str(artwork_literature)
                artwork_images1 = str(artwork_images1)
                artwork_images2 = str(artwork_images2)
                artwork_images3 = str(artwork_images3)
                artwork_images4 = str(artwork_images4)
                artwork_images5 = str(artwork_images5)
                image1_name = str(image1_name)
                image2_name = str(image2_name)
                image3_name = str(image3_name)
                image4_name = str(image4_name)
                image5_name = str(image5_name)
                lot_origin_url = str(lot_origin_url)
                #print(auction_location)
                auction_name = auction_name.replace("&amp;", "&")
                rX = lambda x: " ".join(x.replace(",", "").replace("\n", "").replace("\t", "").replace('"', "").splitlines())
                try:
                    self.fp.write(
                        rX(auction_house_name) + ',' + rX(auction_location) + ',' + rX(auction_num) + ',' + rX(
                            auction_start_date) + ',' + rX(auction_end_date) + ','+rX(auction_name)+','
                        + rX(lot_num) + ',' + rX(sublot_num) + ',' + rX(price_kind) + ',' + rX(
                            price_estimate_min) + ',' + rX(price_estimate_max) + ',' + rX(price_sold) + ',' + rX(
                            artist_name.strip().title()) + ','
                        + rX(artist_birth) + ',' + rX(artish_death) + ',' + rX(artist_nationallity) + ',' + rX(
                            artwork_name.strip().title()) + ',' +
                        rX(artwork_year_identifier) + ',' + rX(artwork_start_year) + ',' + rX(
                            artwork_end_year) + ',' + rX(
                            artwork_materials) + ',' + rX(artwork_category) + ',' + rX(artwork_markings.replace(" l"," l.r")) + ','
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
                    print("Failed writing... %s"%sys.exc_info()[1].__str__())


    def getdatafromjson(self, lotslist):
        #print(lotslist[0].keys())
        titlePattern = re.compile("([^\(]+)\s+\(([^,]+),\s+(\d{4})\-?(\d{0,4})")
        sizePattern1 = re.compile("(\d[\d\.x\s\\\/]+\s*in)")
        sizePattern2 = re.compile("(\d[\d\.x\s\\\/]+\s*cm)")
        sizePattern3 = re.compile("(dia\.?\s+\d[\d\s\.\\\/]+\s*in)")
        mediumPattern = re.compile("(gold)|(silver)|(brass)|(bronze)|(wood)|(porcelain)|(stone)|(marble)|(metal)|(steel)|(iron)|(glass)|(plexiglas)|(chromogenic)|(paper)|(canvas)|(masonite)|(newsprint)|(silkscreen)|(parchment)|(linen)|(inkjet)|(ink\s+jet)|(pigment)|(\stin\s)|(photogravure)|(^oil\s+)|(\s+panel\s+)|(terracotta)|(ivory)|(\s+oak\s+)|(^oak\s+)|(\s+oak$)|(alabaster)|(\s+ink\s+)|(pencil)|(albumen)|(oil\s+)|(\s+oil)|(panel)", re.IGNORECASE|re.DOTALL)
        signedPattern = re.compile("(signed)|(inscribed)", re.IGNORECASE|re.DOTALL)
        literaturePattern = re.compile("Literature\:(.*?)<\/?\s*br>")
        provenancePattern = re.compile("Provenance\:(.*?)<\/?\s*br>")
        auctiondatePattern = re.compile("\"startdate\"\:\"(.*?)\"")
        measureunitPattern = re.compile("(\w{2})\.?\s*$")
        brPattern = re.compile("<br\s*\/?>", re.IGNORECASE)
        emptybracketPattern = re.compile("\(\)")
        beginspacePattern = re.compile("^\s+")
        multispacePattern = re.compile("\s{2,}")
        estimatePattern = re.compile("Estimate", re.IGNORECASE)
        estimaterangePattern = re.compile("Estimate\s+\$[\d\s\-]+")
        yearPattern = re.compile("(\d{4})")
        for lotinfo in lotslist:
            #print(lotinfo.keys())
            auction_house_name, auction_location, auction_num, auction_start_date, auction_end_date = "Skinner", "", "", "", ""
            lot_num, sublot_num, price_kind, price_estimate_min, price_estimate_max, price_sold = "", "", "", "", "", ""
            auction_name, artist_name, artist_birth, artist_death, artist_nationality, artwork_size_notes = "", "", "", "", "", ""
            artwork_provenance, artwork_literature, artwork_exhibited, artwork_description = "", "", "", ""
            artwork_images1, artwork_images2, artwork_images3, artwork_images4, artwork_images5 = "", "", "", "", ""
            image1_name, image2_name, image3_name, image4_name, image5_name = "", "", "", "", ""
            artwork_measurements_height, artwork_measurements_width, artwork_measurements_depth = "", "", ""
            artwork_markings, artwork_edition, artwork_category, artwork_materials, artwork_condition_in = "", "", "", "", ""
            artwork_year_identifier, artwork_start_year, artwork_end_year, auction_measureunit, lot_origin_url = "", "", "", "", ""
            auction_num = self.auctionId
            lotno = lotinfo['lot_number']
            lot_num = str(lotno)
            price_estimate_min = str(lotinfo['estimate_low'])
            price_estimate_max = str(lotinfo['estimate_high'])
            title = lotinfo['title']
            tps = re.search(titlePattern, title)
            artist_name, artist_nationality, artist_birth, artist_death = "", "", "", ""
            if tps:
                artist_name = tps.groups()[0]
                artist_nationality = tps.groups()[1]
                artist_birth = tps.groups()[2]
                artist_death = tps.groups()[3]
            price_sold = lotinfo['sold_price']
            if price_sold == "0" and price_estimate_min != "0":
                price_kind = "estimate"
            elif price_sold != "0":
                price_kind = "price realized"
            else:
                price_kind = "unknown"
            lot_origin_url = "https://live.skinnerinc.com" + lotinfo['_detail_url']
            auction = lotinfo['auction']
            #print(auction)
            auction_name = auction['title']
            #print(auction_name)
            auction_start_date = str(auction['time_start'])
            auction_start_date = auction_start_date.split("T")[0]
            currency = auction['currency_code']
            dimensions = lotinfo['dimensions']
            artwork_start_year = str(lotinfo['when_produced'])
            if not artwork_start_year:
                artwork_start_year = ""
            artwork_size_notes = ""
            if dimensions is not None:
                artwork_size_notes = dimensions
            print("Getting '%s'..."%lot_origin_url)
            detailPageSoup = get_soup(lot_origin_url)
            detailspagecontent = requests.get(lot_origin_url).text
            #ads = re.search(auctiondatePattern, detailspagecontent)
            #if ads:
            #    auction_start_date = ads.groups()[0]
            #    auction_start_date = auction_start_date.split("T")[0]
            productPattern = re.compile("\"product\"\:(\{.*?\})\},")
            pps = re.search(productPattern, detailspagecontent)
            if pps:
                productdatajson = pps.groups()[0]
                productdata = json.loads(productdatajson)
                #print(productdata.keys())
                artwork_name = productdata['name']
                artwork_description = productdata['description']
                artwork_description = artwork_description.replace(";", " ").replace(",", " ")
                #print(artwork_description)
                dsoup = BeautifulSoup(artwork_description, features="html.parser")
                allbtags = dsoup.find_all("b")
                if allbtags.__len__() > 1:
                    artwork_name = allbtags[1].renderContents().decode('utf-8')
                    artwork_name = htmlTagPattern.sub("", artwork_name)
                if re.search(estimatePattern, artwork_name):
                    artwork_name = allbtags[0].renderContents().decode('utf-8')
                print(artwork_name)
                zps1 = re.search(sizePattern1, artwork_description)
                zps2 = re.search(sizePattern2, artwork_description)
                zps3 = re.search(sizePattern3, artwork_description)
                artwork_size_notes = ""
                if zps1:
                    artwork_size_notes = zps1.groups()[0]
                elif zps2:
                    artwork_size_notes = zps2.groups()[0]
                elif zps3:
                    artwork_size_notes = zps3.groups()[0]
                #print(artwork_size_notes)
                sizeparts = artwork_size_notes.split("x")
                if sizeparts.__len__() > 0:
                    artwork_measurements_height = sizeparts[0]
                    mups = re.search(measureunitPattern, artwork_measurements_height)
                    if mups:
                        auction_measureunit = mups.groups()[0]
                        artwork_measurements_height = measureunitPattern.sub("", artwork_measurements_height)
                    if sizeparts.__len__() > 1:
                        artwork_measurements_width = sizeparts[1]
                        mups = re.search(measureunitPattern, artwork_measurements_width)
                        if mups:
                            auction_measureunit = mups.groups()[0]
                            artwork_measurements_width = measureunitPattern.sub("", artwork_measurements_width)
                        if sizeparts.__len__() > 2:
                            artwork_measurements_depth = sizeparts[2]
                            mups = re.search(measureunitPattern, artwork_measurements_depth)
                            if mups:
                                auction_measureunit = mups.groups()[0]
                                artwork_measurements_depth = measureunitPattern.sub("", artwork_measurements_depth)
                descparts = re.split(brPattern, artwork_description)
                #print(descparts)
                if descparts.__len__() > 4:
                    artwork_materials = descparts[4].strip()
                for d in descparts:
                    if artwork_materials == "":
                        if re.search(mediumPattern, d):
                            artwork_materials = d
                            artwork_materials = artwork_materials.replace(artwork_name, "")
                            yps = re.search(yearPattern, artwork_materials)
                            if yps:
                                artwork_start_year = yps.groups()[0]
                                artwork_materials = yearPattern.sub("", artwork_materials)
                    if re.search(signedPattern, d):
                        artwork_markings = d
                artwork_materials = artwork_materials.replace(";", " ").replace(",", " ")
                artwork_markings = artwork_markings.replace(";", " ").replace(",", " ")
                artwork_materials = htmlTagPattern.sub("", artwork_materials)
                artwork_markings = htmlTagPattern.sub("", artwork_markings)
                artwork_materials = sizePattern1.sub("", artwork_materials)
                artwork_materials = sizePattern2.sub("", artwork_materials)
                artwork_materials = sizePattern3.sub("", artwork_materials)
                artwork_materials = emptybracketPattern.sub("", artwork_materials)
                artwork_materials = multispacePattern.sub("", artwork_materials)
                artwork_materials = beginspacePattern.sub("", artwork_materials)
                artwork_materials = estimaterangePattern.sub("", artwork_materials)
                print(artwork_materials)
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
                        if artwork_materials_data.lower() == "huile":
                            artwork_category = "Paintings"
                        if artwork_materials_data.lower() == "technique":
                            artwork_category = "Paintings"
                        if artwork_materials_data.lower() == "toile":
                            artwork_category = "Paintings"
                        if artwork_materials_data.lower() == "color":
                            artwork_category = "Prints"
                except:
                    pass
                try:
                    if artwork_category == '':
                        artwork_materials_data = artwork_materials.strip().replace('\t', '').split(' ')[0]
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
                        if artwork_materials_data.lower() == "huile":
                            artwork_category = "Paintings"
                        if artwork_materials_data.lower() == "color":
                            artwork_category = "Prints"
                except:
                    pass
                lps = re.search(literaturePattern, artwork_description)
                pps = re.search(provenancePattern, artwork_description)
                artwork_literature, artwork_provenance = "", ""
                if lps:
                    artwork_literature = lps.groups()[0]
                if pps:
                    artwork_provenance = pps.groups()[0]
                images = productdata['image']
                if images.__len__() > 0:
                    artwork_images1 = images[0].replace("\\/", "/")
                    #image1_name = scrapperName + '-' + auction_start_date + '-' + self.auctionId + '-' + lot_num + '-' + price_estimate_min + '-a' + '.jpg'
                    processedArtistName = artist_name.replace(" ", "_")
                    processedArtistName = unidecode.unidecode(processedArtistName)
                    image1_name = self.auctionId + "__" + processedArtistName + "__" + str(lotno) + "_a.jpg"
                if images.__len__() > 1:
                    artwork_images2 = images[1].replace("\\/", "/")
                    processedArtistName = artist_name.replace(" ", "_")
                    processedArtistName = unidecode.unidecode(processedArtistName)
                    image2_name = self.auctionId + "__" + processedArtistName + "__" + str(lotno) + "_b.jpg"
                if images.__len__() > 2:
                    artwork_images3 = images[2].replace("\\/", "/")
                    processedArtistName = artist_name.replace(" ", "_")
                    processedArtistName = unidecode.unidecode(processedArtistName)
                    image3_name = self.auctionId + "__" + processedArtistName + "__" + str(lotno) + "_c.jpg"
                if images.__len__() > 3:
                    artwork_images4 = images[3].replace("\\/", "/")
                    processedArtistName = artist_name.replace(" ", "_")
                    processedArtistName = unidecode.unidecode(processedArtistName)
                    image4_name = self.auctionId + "__" + processedArtistName + "__" + str(lotno) + "_d.jpg"
                if images.__len__() > 4:
                    artwork_images5 = images[4].replace("\\/", "/")
                    processedArtistName = artist_name.replace(" ", "_")
                    processedArtistName = unidecode.unidecode(processedArtistName)
                    image5_name = self.auctionId + "__" + processedArtistName + "__" + str(lotno) + "_e.jpg"
            auction_name = auction_name.replace("&amp;", "&")
            price_estimate_min = price_estimate_min.replace(",", "").replace(" ", "")
            price_estimate_max = price_estimate_max.replace(",", "").replace(" ", "")
            price_sold = price_sold.replace(",", "").replace(" ", "")
            rX = lambda x: " ".join(x.replace(",", "").replace("\n", "").replace("\t", "").replace('"', "").splitlines())
            try:
                self.fp.write(
                    rX(auction_house_name) + ',' + rX(auction_location) + ',' + rX(auction_num) + ',' + rX(
                        auction_start_date) + ',' + rX(auction_end_date) + ','+rX(auction_name)+','
                    + rX(lot_num) + ',' + rX(sublot_num) + ',' + rX(price_kind) + ',' + rX(
                        price_estimate_min) + ',' + rX(price_estimate_max) + ',' + rX(price_sold) + ',' + rX(
                        artist_name.strip().title()) + ','
                    + rX(artist_birth) + ',' + rX(artist_death) + ',' + rX(artist_nationality) + ',' + rX(
                        artwork_name.strip().title()) + ',' +
                    rX(artwork_year_identifier) + ',' + rX(artwork_start_year) + ',' + rX(
                        artwork_end_year) + ',' + rX(
                        artwork_materials) + ',' + rX(artwork_category) + ',' + rX(artwork_markings.replace(" l"," l.r")) + ','
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
                print("Failed writing... %s"%sys.exc_info()[1].__str__())

                



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


def updatestatus(auctionno, auctionurl):
    auctionurl = auctionurl.replace("%3A", ":")
    auctionurl = auctionurl.replace("%2F", "/")
    pageurl = "http://216.137.189.57:8080/scrapers/finish/?scrapername=Skinner&auctionnumber=%s&auctionurl=%s&scrapertype=2"%(auctionno, urllib.parse.quote(auctionurl))
    pageResponse = None
    try:
        pageResponse = urllib.request.urlopen(pageurl)
    except:
        print ("Error: %s"%sys.exc_info()[1].__str__())  


if __name__ == "__main__":
    if sys.argv.__len__() < 5:
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
    fp = open(csvpath, "w")
    Scrape(auctionnumber, auctionurl, downloadimages, imagepath, fp)
    fp.close()
    updatestatus(auctionnumber, auctionurl)

# Example: python skinnerinc.py "https://www.skinnerinc.com/auctions/3555B/lots?noredir=1&start=0&display=list&lot=&sort_lot=1&view=1000" 3555B /home/supmit/work/art2/skinner_3555B.csv /home/supmit/work/art2/images/skinner/3555B 0 0




