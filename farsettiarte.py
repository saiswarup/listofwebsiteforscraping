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
#import material_file
#from db import *

from datetime import datetime
import unidecode
import urllib
import urllib.parse


# /// HISTORY/CHANGE LOG -----------------------------------------------------
# DATE            AUTHER                                    ACTION
# 2018-06-19      Saiswarup Sahu <ssahu@artinfo.com>        New version program          Ticket #
# Modified: Supriyo, July 20, 2022.
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

def getDimaision(dim):
    d = dim.replace(".","99999999").replace(",","").replace("x"," ").replace("/","05123450").split(" ")
    dimList = []
    height = "0"
    width = "0"
    depth = "0"
    size = ""
    for rrr in d:
        s = ''.join([i for i in rrr if i.isdigit()])
        if s.__len__() != 0:
            dimList.append(s.replace("99999999",".").replace("05123450","/"))
    for line in dimList:
        if "/" in line:
            index = dimList.index(line)
            dimList[dimList.index(dimList[index-1])] = getDimansionPart(dimList[index-1] +" "+ line)
            dimList[index] = ""
    #print(dimList)
    if dimList.__len__() != 0:
        dimaisionList = dimList
        if dimaisionList.__len__() == 3 or dimaisionList.__len__() > 3:
            height = dimaisionList[0]
            width = dimaisionList[1]
            depth = dimaisionList[2]
            size = height + " x " + width + " x " + depth
        if dimaisionList.__len__() == 2:
            height = dimaisionList[0]
            width = dimaisionList[1]
            depth = "0"
            size = height + " x " + width
        if dimaisionList.__len__() == 1:
            height = dimaisionList[0]
            width = "0"
            depth = "0"
            size = height
        return height,width,depth,size
    else:
        return "0","0","0","",None


def getMaterial(descriptionList):
    mediumPattern = re.compile("(gold)|(silver)|(brass)|(bronze)|(wood)|(porcelain)|(stone)|(marble)|(metal)|(steel)|(iron)|(glass)|(plexiglas)|(chromogenic)|(paper)|(canvas)|(masonite)|(newsprint)|(silkscreen)|(parchment)|(linen)|(inkjet)|(ink\s+jet)|(pigment)|(\stin\s)|(photogravure)|(^oil\s+)|(\s+panel\s+)|(terracotta)|(ivory)|(\s+oak\s+)|(^oak\s+)|(\s+oak$)|(alabaster)|(\s+ink\s+)|(pencil)|(albumen)|(oil\s+)|(\s+oil)|(panel)|(acrylic)|(print)|(Huile)|(toile)|(plume)|(encre)|(lavis)|(Gravure)|(Pierre)|(pastel)|(panneau)|(Sanguine)|(Crayon)|(aquarelle)|(papier)|(stampa\s+offset)|(tappeto)", re.DOTALL|re.IGNORECASE)
    try:
        materialList = [x for x in descriptionList if re.search(
                            materialDict["material"],
                        x.lower()) and yearExtract(
                        x).__len__() == 0 and "numbered" not in x.lower() and "date" not in x.lower()
                                    and ":" not in x and "framed" not in x.lower()
                        and "cm" not in x.lower() and "marked" not in x.lower() and "sign" not in x.lower() and "label" not in x.lower()]
        material = materialList[0].strip()
        if "bronze" in material:
            material = "bronze"
        mps = re.search(mediumPattern, material)
        if mps:
            material = mps.groups()[0]
        if "(" in material:
            material=material.split("(")[0].strip()
        return material
    except:
        return ""


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
        self.domainUrl = "https://www.farsettiarte.it"
        self.downloadImages = downloadImages
        self.scrapperName = "Farsettiarte"
        self.fp = fp
        self.run()

    def run(self):
        nextPage = True
        soup = get_soup(self.mainUrl)
        self.writeHeaders(soup)  # Write the header part of csv
        try:
            total_page_nos = 24
        except:
            total_page_nos = ""
            pass
        httpHeaders = { 'User-Agent' : r'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36',  'Accept' : 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9', 'Accept-Language' : 'en-us,en;q=0.5', 'Accept-Encoding' : 'gzip,deflate', 'Accept-Charset' : 'ISO-8859-1,utf-8;q=0.7,*;q=0.7', 'Connection' : 'keep-alive', }
        httpHeaders['cache-control'] = "max-age=0"
        httpHeaders['sec-ch-ua'] = "\".Not/A)Brand\";v=\"99\", \"Google Chrome\";v=\"103\", \"Chromium\";v=\"103\""
        httpHeaders['sec-ch-ua-mobile'] = "?0"
        httpHeaders['sec-ch-ua-platform'] = "Linux"
        httpHeaders['upgrade-insecure-requests'] = "1"
        httpHeaders['sec-fetch-dest'] = "document"
        httpHeaders['sec-fetch-mode'] = "navigate"
        httpHeaders['sec-fetch-site'] = "same-origin"
        httpHeaders['sec-fetch-user'] = "?1"
        httpHeaders['referer'] = self.mainUrl
        auctionurlparts = auctionUrl.split("?")
        aucurl = auctionurlparts[0]
        next_page_urls = [aucurl +"?pag="+ str(x) + "#catalogue" for x in range(1, total_page_nos + 1)]
        pagectr = 1
        for page_url in next_page_urls:
            print(page_url)
            #d = datetime.now()
            #dd = d.strftime("%Y-%m-%dT%H:%M:%SZ")
            #dd = dd.replace(":", "%3A")
            #httpHeaders['cookie'] = "registrazione%5FCasa+d%27aste+Farsettiarte=pagineVis=" + str(pagectr) + "&attivato=0;_jsuid=1397622566; _heatmaps_g2g_100718721=no; _iub_cs-97000345=%7B%22timestamp%22%3A%22" + str(dd) + "%22%2C%22version%22%3A%221.40.0%22%2C%22purposes%22%3A%7B%221%22%3Atrue%2C%224%22%3Atrue%7D%2C%22id%22%3A97000345%2C%22cons%22%3A%7B%22rand%22%3A%22869ac2%22%7D%7D;"
            #httpHeaders['cookie'] = "registrazione%5FCasa+d%27aste+Farsettiarte=pagineVis=1&attivato=0; ASPSESSIONIDQGCSARAS=NMLHBBPCKEEMIBBNDKDLLKLP; _fbp=fb.1.1658238082444.1245240520; _ga=GA1.2.1260475549.1658238083; _gid=GA1.2.1409088931.1658238083; _jsuid=1397622566; _heatmaps_g2g_100718721=no; _iub_cs-97000345=%7B%22timestamp%22%3A%222022-07-19T13%3A41%3A43.245Z%22%2C%22version%22%3A%221.40.0%22%2C%22purposes%22%3A%7B%221%22%3Atrue%2C%224%22%3Atrue%7D%2C%22id%22%3A97000345%2C%22cons%22%3A%7B%22rand%22%3A%22869ac2%22%7D%7D; _ga_GTGLLXD3VR=GS1.1.1658238082.1.1.1658238108.0"
            pagectr += 1
            soup = get_soup(page_url, httpHeaders=httpHeaders)
            productDetails = soup.findAll('div', {'class': 'image-holder-list'})#?pag=2
            for product in productDetails:
                auction_house_name = "Farsettiarte"
                auction_location = "Toronto"
                auction_num = ""
                auction_start_date = ""
                auction_end_date = ""
                auction_name = ''
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

                aTag = product.find("a")['href']
                try:
                    lot_origin_url = aTag
                except:
                    pass
                try:
                    detailPageSoup = get_soup(aTag)
                except:
                    pass
                try:
                    lot_num = ''.join(re.findall('\d+',detailPageSoup.find('div',{'class':'number'}).getText().strip()))
                    print(lot_num)
                except:
                    pass
                try:
                    artist_name_data = detailPageSoup.find('div',{'id': 'autore'})
                except:
                    pass
                try:
                    artist_name = re.sub("['('].*",'',artist_name_data.getText())
                except:
                    pass
                try:
                    artist_nationallity = detailPageSoup.find('div',{'class': 'dateAuthor'}).getText().replace("['(']","").replace("[')']","")
                    artist_nationallity=''.join(re.findall("['('](.*?\s)",artist_nationallity))
                    artist_nationallity=re.sub("[')']","",artist_nationallity)
                    #print(artist_nationallity)
                except:
                    pass
                try:
                    years = re.findall("\d{4}", artist_name_data.getText())
                    artist_birth, artish_death = ['', '']
                    if len(years) > 1:
                        artist_birth = years[0]
                        artish_death = years[1]
                    elif len(years) == 1:
                        artist_birth = years[0]
                except:
                    pass
                try:
                    artwork_name = detailPageSoup.find('div',{'id': 'titleLotto'}).getText()
                except:
                    pass
                try:
                    artwork_start_year, artwork_end_year = getStartEndYear(artwork_name)
                except:
                    pass
                try:
                    estimation = detailPageSoup.find('b',{'class':'didascalia'}).getText()
                    priceList = re.findall('\d+',estimation)
                    if priceList.__len__() == 2:
                        price_estimate_min = ''.join(re.findall("\d+", X(priceList[0].strip())))
                        price_estimate_max = ''.join(re.findall("\d+", X(priceList[1].strip())))
                    if priceList.__len__() == 1:
                        price_estimate_min = ''.join(re.findall("\d+", X(priceList[0].strip())))
                        price_estimate_max = "0"
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
                    All_Data = detailPageSoup.find('div', {'class': 'OperaText'}).getText(separator=u'@').strip().replace('@@@', '@').replace('@@', '@').split("@")
                except:
                    pass
                try:
                    artwork_materials = getMaterial(All_Data)
                    print(artwork_materials)
                except:
                    pass
                try:
                    artwork_markings = getSignature(All_Data)
                except:
                    pass
                try:
                    dimension = [x for x in All_Data if "cm." in x.strip().lower()]
                    dimension = dimension[0].replace(',', '.').replace("cm.","").strip()
                    auction_measureunit = 'cm'
                    dimaisionList = getDimaision(dimension)
                    artwork_measurements_height = dimaisionList[0].replace("1.9", "19.").replace(".9", "9.")
                    artwork_measurements_width = dimaisionList[1].replace("1.9", "19.").replace(".9", "9.")
                    artwork_measurements_depth = dimaisionList[2].replace("1.9", "19.").replace(".9", "9.")
                except:
                    pass
                try:
                    artwork_size_notes = artwork_measurements_height + 'x' + artwork_measurements_width + 'x' + artwork_measurements_depth + " " + 'cm'
                    endxPattern = re.compile("x\.?\s+(cm)|(in)")
                    artwork_size_notes = endxPattern.sub(" cm", artwork_size_notes)
                    print(artwork_size_notes)
                except:
                    pass

                try:
                    auction_name = detailPageSoup.find('h2',{'class': 'mb-0'}).getText()
                except:
                    pass
                try:
                    auction_num=''.join(re.findall('\d+',auction_name))
                except:
                    pass
                try:
                    artwork_images1 = 'https://www.farsettiarte.it' + detailPageSoup.find("div", {"class": "stageImg"}).find("img")['src']
                    #image1_name = scrapperName + '-' + auction_location + '-'+auction_num+ '-'+auction_name+'-'+auction_start_date + '-' + lot_num.strip()+ '-a' + '.jpg'
                    processedArtistName = artist_name.replace(" ", "_")
                    processedArtistName = unidecode.unidecode(processedArtistName)
                    newname1 = str(auction_num) + "__" + processedArtistName + "__" + str(lot_num).strip() + "_a.jpg"
                    image1_name = newname1
                    image1_name=re.sub(r"\s+", "", image1_name, flags=re.UNICODE)
                except:
                    pass
                try:
                    date_time_auction_details = detailPageSoup.find('div',{'class': 'dataAsta'}).getText().strip().split(' ')
                    auction_start_date = ''.join(re.findall('\d+',date_time_auction_details[-3])) + '-' + date_time_auction_details[-2][:3] + '-' + date_time_auction_details[-1][-2:]
                except:
                    pass
                try:
                    artwork_description = "<strong><br>Description:</strong><br>" + lot_num+' '+detailPageSoup.find('div',{'id':'autore'}).getText(separator=u'  ')+' '+detailPageSoup.find('div',{'id':'titleLotto'}).getText(separator=u'  ')+' '+detailPageSoup.find('div',{'id':'descLotto'}).getText(separator=u'  ')
                except:
                    pass
                try:
                    fun=translatToEnglish(artwork_materials)
                except:
                    pass
                try:
                    if artwork_materials.__len__() != 0 or artwork_materials != "":
                        artwork_materials_data = fun.replace(',', '').split(' ')[0]
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
                        if artwork_materials_data == "Olio":
                            artwork_category = "Prints"
                        if artwork_materials_data == "Tempera":
                            artwork_category = "Prints"
                        if artwork_materials_data == "Scultura":
                            artwork_category = "Sculptures"
                except:
                    pass

                rX = lambda x: " ".join(x.replace(",", "").replace("\n", "").replace("\t", "").replace('"', "").splitlines())
                artwork_markings = artwork_markings.replace('"', "'").replace(";", " ")
                artwork_description = artwork_description.replace('"', "'").replace(";", " ")
                artwork_materials = artwork_materials.replace('"', "'").replace(";", " ")
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
                            artwork_materials) + ',' + rX(artwork_category) + ',' + rX(artwork_markings.strip()) + ','
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


    def writeHeaders(self, soup):
        auction_name, auction_date, auction_title, auction_location, lotCount, lot_sold_in = "", "", "", "", "", ""
        lot_sold_in = "USD"

        writeHeader(self.fp, auction_name, auction_location, auction_date, auction_title, auctionId, lotCount,
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
    pageurl = "http://216.137.189.57:8080/scrapers/finish/?scrapername=Farsettiarte&auctionnumber=%s&auctionurl=%s&scrapertype=2"%(auctionno, urllib.parse.quote(auctionurl))
    pageResponse = None
    try:
        pageResponse = urllib.request.urlopen(pageurl)
    except:
        print ("Error: %s"%sys.exc_info()[1].__str__())  



if __name__ == "__main__":
    if sys.argv.__len__() < 5:
        print("Insufficient parameters")
        sys.exit()
    auctionUrl = sys.argv[1]
    auctionId = sys.argv[2]
    csvpath = sys.argv[3]
    imagepath = sys.argv[4]
    downloadImages = 0
    convertfractions = 0
    if sys.argv.__len__() > 5:
        downloadImages = sys.argv[5]
    if sys.argv.__len__() > 6:
        convertfractions = sys.argv[6]
    fp = open(csvpath, "w")
    Scrape(auctionId, auctionUrl, downloadImages, fp)
    fp.close()
    updatestatus(auctionId, auctionUrl)


# Sample command to run: python farsettiarte.py https://www.farsettiarte.it/uk/auction-0215-1/parade.asp?action=reset 0215 /home/supmit/work/art2/farsettiarte_0215.csv /home/supmit/work/art2/images/farsettiarte/0215 0 0



