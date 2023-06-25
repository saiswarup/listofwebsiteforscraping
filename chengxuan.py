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
from cryptography.fernet import Fernet
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
    def __init__(self, mainUrl, auctionId, csvpath, imagedir, downloadImages, scrapperName,  fp):
        self.auctionId = auctionId
        self.mainUrl = mainUrl
        self.domainUrl = "http://en.chengxuan.com"
        self.imagedir = imagedir
        self.downloadImages = downloadImages
        self.scrapperName = scrapperName
        self.fp = fp
        self.run(auctionId, csvpath, self.imagedir)


    def getImagenameFromUrl(self, imageUrl):
        urlparts = imageUrl.split("/")
        imagefilepart = urlparts[-1]
        imagefilenameparts = imagefilepart.split("?")
        imagefilename = imagefilenameparts[0]
        return imagefilename


    def encryptFilename(self, filename):
        k = Fernet.generate_key()
        f = Fernet(k)
        encfilename = f.encrypt(filename.encode())
        return encfilename


    def run(self, auctionId, csvpath, imagedir):
        nextPage = True
        soup = get_soup(self.mainUrl)
        self.writeHeaders(soup)  # Write the header part of csv
        last_page_count = 10
        for page_no in range(1, last_page_count):
            url="http://en.chengxuan.com/subactivity/"+auctionId+"/page"+str(page_no)+"/?sort_order=by_number"
            soup = get_soup(url)
            tablesoup = soup.find('table', {'id' : 'table_style'})
            if not tablesoup:
                continue
            productDetails = tablesoup.find('tbody').findAll('td',{"align":"left"})
            for product in productDetails:
                auction_house_name = "Chengxuan Auctions"
                auction_location = ""
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
                subLot=''
                artwork_measurements_depth='0'
                aTag = product.find("a")

                if aTag:
                    detailPageUrl = "http://en.chengxuan.com"+aTag["href"]
                    #print(detailPageUrl),'_____'
                    try:
                        lot_origin_url = detailPageUrl
                    except:
                        pass
                    try:
                        detailPageSoup = get_soup(detailPageUrl)
                        lotDetails = detailPageSoup.find('div', {'class': 'item-description'})
                        lotDetails = lotDetails.findAll('p')
                    except:
                        pass
                    ########lotNumber########
                    try:
                        lot_num = ''.join(re.findall("Lot.*(\s\d+)", lotDetails[0].getText()))
                    except:
                        pass

                    try:
                        artwork_name=lotDetails[1].getText().title().strip()
                        if "   " in artwork_name:
                            artwork_name_lot=artwork_name.split('   ')
                            if artwork_name_lot.__len__() >= 2:
                                artist_name = X(artwork_name_lot[0].strip())
                                #print(artist_name)
                                artwork_name = X(artwork_name_lot[1].strip())
                        elif "  " in artwork_name:
                            artwork_name_lot=artwork_name.split('  ')
                            if artwork_name_lot.__len__() >= 2:
                                artist_name = X(artwork_name_lot[0].strip())
                                artwork_name = X(artwork_name_lot[1].strip())
                        elif ',' in artwork_name:
                            artwork_name_lot=artwork_name.split(',')
                            if artwork_name_lot.__len__() == 2:
                                artist_name = X(artwork_name_lot[0].strip())
                                #print(artist_name + " ####")
                                artwork_name = X(artwork_name_lot[1].strip())
                    except:
                        pass
                    try:
                        All_Data = detailPageSoup.find('div', {'class': 'item-description'}).getText(separator=u'@').strip().replace('@@@', '@').replace('@@', '@')
                        All_Data = All_Data.split('@')
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
                        price_sold = [x for x in All_Data if "Selling Price" in x.strip()]
                        if price_sold.__len__() != 0:
                            price_sold = price_sold[0]
                            price_sold = ''.join(re.findall("\d+", price_sold.strip()))
                        else:
                            price_sold = '0'
                    except:
                        price_sold='0'
                        pass
                    if price_sold == "0" and price_estimate_min != "0":
                        price_kind = "estimate"
                    elif price_sold != "0":
                        price_kind = "price realized"
                    else:
                        price_kind = "unknown"

                    try:
                        dimension = [x for x in All_Data if "cm." in x.strip().lower()]
                        dimension = dimension[0]
                        auction_measureunit = 'cm'
                        size = dimension.replace('&nbsp;', ' ').strip()
                        dimension = ''.join(re.findall("SIZE:\s(.*?)\scm.", size))
                        dimension = re.findall("[-+]?\d*\.\d+|\d+", size)
                        artwork_measurements_height = str(dimension[0].strip())
                        if dimension.__len__() >= 1:
                            artwork_measurements_height = str(dimension[0].strip())
                            artwork_measurements_width = str(dimension[1].strip())
                    except:
                        pass
                    auction_measureunit = 'cm'
                    try:
                            conditionList = [x for x in All_Data if
                                             "framed" in x.lower() or "good" in x.lower() or "giltwood" in x.lower() or "unframed" in x.lower()
                                             or "incorniciato" in x.lower() or "bene" in x.lower() or "senza cornice" in x.lower()
                                             or "encadr" in x.lower() or "bien" in x.lower() or "bois dor" in x.lower()
                                             or "sans cadre" in x.lower()]
                            if conditionList.__len__() > 1:
                                artwork_condition_in = " ".join(conditionList).strip()
                            else:
                                artwork_condition_in = conditionList[0].strip()
                    except:
                        pass
                    try:
                        artwork_materials = getMaterial(detailPageSoup.find('div', {'class': 'item-description'}).getText(separator=u'@').split("@"))
                    except:
                        pass

                    if artwork_materials=='':
                        try:
                            artwork_materials = [x for x in All_Data if "TEXTURE" in x]
                            if artwork_materials.__len__() > 1:
                                artwork_materials = " ".join(artwork_materials).strip().replace("TEXTURE",'').replace(":","")
                            else:
                                artwork_materials = artwork_materials[0].strip().replace("TEXTURE",'').replace(":","")
                        except:
                            pass
                    if "," in  artwork_materials:
                        artwork_materials_lot=artwork_materials.split(',')
                        print(artwork_materials)
                        artwork_condition_in=artwork_materials_lot[0].strip()
                        artwork_materials=artwork_materials_lot[-1].strip()
                    else:
                        pass
                    try:
                        artwork_markings = getSignature(All_Data)
                        artwork_edition = ''.join(re.findall('numbered \'?(\d+\/\d+)\'?.*', artwork_markings))
                        artwork_edition = artwork_edition.replace('/', ' of ')
                    except:
                        pass
                    try:
                        if artwork_edition == '':
                            artwork_edition = getEditionOf(artwork_markings)
                    except:
                        artwork_edition = ''
                        pass
                    try:
                        artwork_size_notes = artwork_measurements_height + 'x' + artwork_measurements_width + 'x' + artwork_measurements_depth + " " + 'cm'
                    except:
                        pass
                    try:
                        lot_num, sublot_num = getSubLot(lot_num)
                    except:
                        pass
                    try:
                        artwork_description = "<strong><br>Description:</strong><br>" + str(detailPageSoup.find('div', {'class': 'item-description'}).getText(separator=u'@').replace('\t','').replace('\n','').replace('Prev','').replace('Lot','').replace('Next','').replace('Top','').replace('@@','@').replace('@',' ').replace('|',''))
                    except:
                        pass
                    try:
                        date=detailPageSoup.find("dl",{'class':'left-column list-unstyle'}).find('p').getText(separator=u'_').split('_')[0].strip().split('at')[0].split(' ')[1]
                        months=detailPageSoup.find("dl",{'class':'left-column list-unstyle'}).find('p').getText(separator=u'_').split('_')[0].strip().split('at')[0].split(' ')[0][0:3]
                        year=detailPageSoup.find("dl",{'class':'left-column list-unstyle'}).find('span',{'class':'year'}).getText()[-2:]

                        auction_start_date=date+'-'+months.replace('.','')+'-'+year
                        #print(auction_start_date)
                    except:
                        pass
                    try:
                        auction_name=detailPageSoup.find("ul",{'class':'breadcrumb list-unstyle list-inline'}).findAll("li")[-1].getText()
                        auction_location='Beijing'
                    except:
                        pass
                    try:
                        lot_num, sublot_num = getSubLot(lot_num)
                        #print(sublot_num), '0000000000'
                    except:
                        pass
                    try:
                        artwork_images1 = detailPageSoup.find("div", {"class": "picture-suite"}).find("a")['href']
                        image1_name = scrapperName +'_'+auction_location+'_'+auction_start_date+'-'+auctionId+ '_' + lot_num +'_' +price_estimate_min+'-a'+'.jpg'
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
                    except:
                        pass

                    try:
                        if artwork_category=='':
                            artwork_materials_data = artwork_materials.strip().replace('\t','').split(' ')[0]
                            #print(artwork_materials_data),'saisidididhdihdihd'
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
                    except:
                        pass
                    auction_num=auctionId
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
                    imagename1 = self.getImagenameFromUrl(artwork_images1)
                    imagename1 = str(imagename1)
                    imagename1 = imagename1.replace("b'", "").replace("'", "")
                    processedAuctionTitle = auction_name.replace(" ", "_")
                    processedArtistName = artist_name.replace(" ", "_")
                    processedArtistName = unidecode.unidecode(processedArtistName)
                    processedArtworkName = artwork_name.replace(" ", "_")
                    sublot_number = ""
                    #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + self.auctionId + "__" + str(lot_num) + "__" + sublot_number
                    newname1 = self.auctionId + "__" + processedArtistName + "__" + str(lot_num) + "_a"
                    #encryptedFilename = self.encryptFilename(newname1)
                    encryptedFilename = newname1
                    imagepathparts = artwork_images1.split("/")
                    defimageurl = "/".join(imagepathparts[:-2])
                    encryptedFilename = str(encryptedFilename).replace("b'", "")
                    encryptedFilename = str(encryptedFilename).replace("'", "")
                    image1_name = str(encryptedFilename) + ".jpg"
                    image2_name = str(image2_name)
                    image3_name = str(image3_name)
                    image4_name = str(image4_name)
                    image5_name = str(image5_name)
                    lot_origin_url = str(lot_origin_url)
                    if artist_name == "":
                        artist_name = str(artwork_name.split('\xc2')[0])
                    artwork_name = str(artwork_name.split('\xc2')[-1])
                    artist_name=artist_name.replace(artwork_name,'').strip()
                    artwork_start_year=''.join(re.findall('\d+',artist_name))
                    artist_name=artist_name.replace(artwork_start_year,'')
                    rX = lambda x: " ".join(x.replace(",", "").replace("\n", "")
                                            .replace("\t", "").replace('"',
                                                                       "").splitlines())  # This function remove coma and new lines
                    if lot_num.__len__() != 0 or lot_num != "":
                        fp.write(rX(auction_house_name) + ',' + rX(auction_location) + ',' + rX(auction_num) + ',' + rX(
                            auction_start_date) + ',' + rX(auction_end_date) + ',' + rX(auction_name) + ','
                                 + rX(lot_num) + ',' + rX(subLot) + ',' + rX(price_kind) + ',' + rX(
                            price_estimate_min) + ',' + rX(price_estimate_max) + ',' + rX(price_sold) + ',' + rX(
                            artist_name.strip()) + ','
                                 + rX(artist_birth) + ',' + rX(artish_death) + ',' + rX(artist_nationallity) + ',' + rX(
                            artwork_name.strip()) + ',' +
                                 rX(artwork_year_identifier) + ',' + rX(artwork_start_year) + ',' + rX(
                            artwork_end_year) + ',' + rX(
                            artwork_materials.strip()) + ',' + rX(artwork_category) + ',' + rX(artwork_markings) + ','
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
    pageurl = "http://216.137.189.57:8080/scrapers/finish/?scrapername=Chengxuan&auctionnumber=%s&auctionurl=%s&scrapertype=2"%(auctionno, urllib.parse.quote(auctionurl))
    pageResponse = None
    try:
        pageResponse = urllib.request.urlopen(pageurl)
    except:
        print ("Error: %s"%sys.exc_info()[1].__str__())  



if __name__ == "__main__":
    auctionId = sys.argv[2].upper()
    mainUrl = sys.argv[1]
    csvpath = sys.argv[3]
    imagedir = sys.argv[4]
    scrapperName = "chengxuan"
    downloadImages = False
    if sys.argv.__len__() > 2 and sys.argv[2] == "True":
        downloadImages = "True"
    fp = open(csvpath, "w")
    Scrape(mainUrl, auctionId, csvpath, imagedir, downloadImages, scrapperName,  fp)
    fp.close()
    updatestatus(auctionId, mainUrl)


# Example: python chengxuan.py "http://en.chengxuan.com/subactivity/511/" 511 /home/supmit/work/art2/chengxuan_511.csv /home/supmit/work/art2/images/chengxuan/511 0 0


