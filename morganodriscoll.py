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

def getDimaision_own(dim):
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
    dimList = list(filter(None,dimList))
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


class Scrape:
    def __init__(self, mainUrl, auctionId, csvpath, imagedir, downloadImages, scrapperName, fp):
        self.auctionId = auctionId
        self.mainUrl = mainUrl
        self.imagedir = imagedir
        self.domainUrl = "https://www.morganodriscoll.com"
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
        try:
            total_page_nos = 24
        except:
            total_page_nos = ""
            pass
        next_page_urls = [self.mainUrl +"/"+ str(x) for x in range(0, total_page_nos + 1)]
        for page_url in next_page_urls:
            soup = get_soup(page_url)

            productDetails = soup.findAll("div", {'class' : 'bxr aucBox'})
            #print(len(productDetails))
            for product in productDetails:
                auction_house_name = "Morgan O'Driscoll"
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
                artwork_measurements_depth='0'

                try:
                    aTag = product.find("a")
                    #print(aTag)
                except:
                    aTag = None
                    pass
                if aTag:
                    detailPageUrl = 'https://www.morganodriscoll.com'+product.find("a")['href']
                    #print(detailPageUrl)
                    try:
                        lot_origin_url=detailPageUrl
                    except:
                        pass
                    detailPageSoup = get_soup(detailPageUrl)
                    try:
                        lot_num = detailPageSoup.find("div", {"class": "deCell"}).getText()
                        lot_num=''.join(re.findall("\d+",lot_num))
                        print ("lotNum:-%s"%lot_num)
                    except:
                        pass
                    try:
                        artist_name = detailPageSoup.find('span',{'class': 'deArtist'}).getText().encode('ascii', 'ignore').decode('ascii')
                        #print("artist_name:-"), artist_name
                    except:
                        pass
                    try:
                        artist_birth, artish_death = getStartEndYear(artist_name)
                        artist_name = re.sub("['('].*", '', artist_name)
                    except:
                        pass
                    try:
                        artwork_name=detailPageSoup.find('header').find('h1').getText()
                        #print("artwork_name:-"), artwork_name
                    except:
                        pass
                    try:
                        artwork_start_year, artwork_end_year = getStartEndYear(artwork_name)
                        artwork_name = re.sub("['('].*", '', artwork_name)
                    except:
                        pass
                    try:
                        All_Data = detailPageSoup.find('div', {'class': 'mobPad'}).getText(separator=u'@').strip().replace('@@@', '@').replace('@@', '@').split("@")
                    except:
                        pass
                    try:
                        dimension = [x for x in All_Data if "cm" in x.strip().lower()]
                        #print(dimension)
                        dimension = dimension[0].replace(',', '.').replace("in.","").strip().replace('-',' ')
                        dimension=re.sub("cm.*","",dimension)
                        #print(dimension)
                        auction_measureunit = 'cm'
                        dimaisionList = getDimaision_own(dimension)
                        artwork_measurements_height = dimaisionList[0].replace("1.9", "19.").replace(".9", "9.")
                        artwork_measurements_width = dimaisionList[1].replace("1.9", "19.").replace(".9", "9.")
                        artwork_measurements_depth = dimaisionList[2].replace("1.9", "19.").replace(".9", "9.")
                    except:
                        pass
                    try:
                        artwork_size_notes = artwork_measurements_height + 'x' + artwork_measurements_width + " " + 'cm'
                    except:
                        pass
                    try:
                        artwork_markings = getSignature(All_Data)
                        artwork_markings=artwork_markings.replace("Title","").replace("Signature","").replace(":","").replace(";","")
                    except:
                        pass
                    try:
                        artwork_materials = getMaterial(All_Data)
                    except:
                        pass
                    try:
                        priceRealized = All_Data[4]
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
                    try:
                        images=detailPageSoup.find('ul',{'id':'gallery_01'}).findAll("a")
                    except:
                        pass
                    #print(images)
                    try:
                        artwork_images1 = images[0]['href']
                        #print(artwork_images1)
                        #image1_name = scrapperName + '-' + auction_start_date + '-' + auctionId + '-' + lot_num + '-' + price_estimate_min + '-a' + '.jpg'
                        processedArtistName = artist_name.replace(" ", "_")
                        processedArtistName = unidecode.unidecode(processedArtistName)
                        image1_name = auctionId + "__" + processedArtistName + "__" + str(lot_num) + "_a.jpg"
                        image1_name = image1_name.replace('_', '-')
                    except:
                        pass
                    try:
                        artwork_images2 = images[1]['href']
                        #print(artwork_images2)
                        #image2_name = scrapperName + '-' + auction_start_date + '-' + auctionId + '-' + lot_num + '-' + price_estimate_min + '-b' + '.jpg'
                        processedArtistName = artist_name.replace(" ", "_")
                        processedArtistName = unidecode.unidecode(processedArtistName)
                        image2_name = auctionId + "__" + processedArtistName + "__" + str(lot_num) + "_b.jpg"
                        image2_name = image2_name.replace('_', '-')
                    except:
                        pass
                    try:
                        artwork_images3 = images[2]['href']
                        #print(artwork_images3)
                        #image3_name = scrapperName + '-' + auction_start_date + '-' + auctionId + '-' + lot_num + '-' + price_estimate_min + '-c' + '.jpg'
                        processedArtistName = artist_name.replace(" ", "_")
                        processedArtistName = unidecode.unidecode(processedArtistName)
                        image3_name = auctionId + "__" + processedArtistName + "__" + str(lot_num) + "_c.jpg"
                        image3_name = image3_name.replace('_', '-')
                    except:
                        pass
                    try:
                        artwork_images4 = images[3]['href']
                        #print(artwork_images4)
                        #image4_name = scrapperName + '-' + auction_start_date + '-' + auctionId + '-' + lot_num + '-' + price_estimate_min + '-d' + '.jpg'
                        processedArtistName = artist_name.replace(" ", "_")
                        processedArtistName = unidecode.unidecode(processedArtistName)
                        image4_name = auctionId + "__" + processedArtistName + "__" + str(lot_num) + "_d.jpg"
                        image4_name = image4_name.replace('_', '-')
                    except:
                        pass
                    try:
                        artwork_images5 = images[4]['href']
                        #print(artwork_images5)
                        #image5_name = scrapperName + '-' + auction_start_date + '-' + auctionId + '-' + lot_num + '-' + price_estimate_min + '-e' + '.jpg'
                        processedArtistName = artist_name.replace(" ", "_")
                        processedArtistName = unidecode.unidecode(processedArtistName)
                        image5_name = auctionId + "__" + processedArtistName + "__" + str(lot_num) + "_e.jpg"
                        image5_name = image5_name.replace('_', '-')
                    except:
                        pass
                    auction_name = \
                    detailPageSoup.find("div", {"class": "fl"}).find('span').getText(separator=u'@').split("@")[0]
                    #print(auction_name)
                    try:
                        auction_date = \
                        detailPageSoup.find("div", {"class": "fl"}).find('span').getText(separator=u'@').split("@")[1]
                        auction_date = ''.join(re.findall("\d.*", auction_date))
                        auction_start_date = ''.join(re.findall("\d+", auction_date.strip().split(' ')[0])) + '-' + \
                                             auction_date.strip().split(' ')[1][:3] + '-' + "17"#auction_date.strip().split(' ')[-1][-2:]
                        #print(auction_start_date)
                        auction_start_date='24-Sep-12'
                    except:
                        pass

                    auction_start_date = '12-Nov-18'
                    auction_num = self.mainUrl.split("/")[-1]
                    auction_location = 'Cork'
                    data = detailPageSoup.findAll("div", {"class": "detRow detRowSm"})
                    #print(data)
                    for dataSpan in data:
                        dataSpanText = dataSpan.getText().encode('ascii', 'ignore').decode('ascii').replace("\n", '')
                        #print(dataSpanText)
                        artwork_provenance = ''.join(re.findall("Provenance:.*", dataSpanText)).strip().replace("Provenance:", "").strip()
                        if artwork_materials == '':
                            artwork_materials = ''.join(re.findall("Medium:.*", dataSpanText)).strip().replace("Medium:", "")

                    try:
                        artwork_markings = detailPageSoup.find("div", {"class": "detRow detRowSm mt10"}).findAll("span")[-1].getText()
                    except:
                        pass
                    try:
                        artwork_edition=getEditionOf(artwork_markings)
                    except:
                        pass
                    try:
                        artwork_exhibited=''.join(re.findall("Exhibited:.*", dataSpanText)).strip().replace("Exhibited:", "")
                    except:
                        pass
                    try:
                        artwork_literature=''.join(re.findall("Literature:.*", dataSpanText)).strip().replace("Literature:", "")
                    except:
                        pass
                    try:
                        artwork_description = "<strong><br>Description:</strong><br>" + '  ' + lot_num + '  ' + price_sold + "  " + artwork_name + '.' + artist_name + '.' + artwork_materials + "." + artwork_markings + '.' + "<strong><br>Provenance:</strong><br>" + '' + artwork_provenance#+ '.' + "<strong><br>Exhibited:</strong><br>" + '' + artwork_exhibited+ '.' + "<strong><br>Literature:</strong><br>" + '' + artwork_literature
                        artwork_description = artwork_description.replace('"', "&quot;").replace("'", "&quot;")
                        artwork_description = artwork_description.replace(';', " ").replace(",", " ")
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
                            if artwork_materials_data.lower() == "huile":
                                artwork_category = "Paintings"
                            if artwork_materials_data.lower() == "technique":
                                artwork_category = "Paintings"
                            if artwork_materials_data.lower() == "toile":
                                artwork_category = "Paintings"
                            if artwork_materials_data.lower() == "color":
                                artwork_category = "Prints"
                            if artwork_materials_data.lower() == "watercolour":
                                artwork_category = "Works on paper"
                    except:
                        pass


                    try:
                        rX = lambda x: " ".join(
                            x.replace(",", ".").replace("\n", "").replace("\t", "").replace('"', "").splitlines())
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
                    except:
                        pass







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
    pageurl = "http://216.137.189.57:8080/scrapers/finish/?scrapername=MorganODriscoll&auctionnumber=%s&auctionurl=%s&scrapertype=2"%(auctionno, urllib.parse.quote(auctionurl))
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
    domainUrl = ''
    scrapperName = "Morgan O'Driscoll"
    downloadImages = True
    if sys.argv.__len__() > 2 and sys.argv[2] == "True":
        downloadImages = "True"
    fp = open(csvpath, "w")
    Scrape(mainUrl, auctionId, csvpath, imagedir, downloadImages, scrapperName,  fp)
    fp.close()
    updatestatus(auctionId, mainUrl)
    
# Example: python morganodriscoll.py "https://www.morganodriscoll.com/auction/important-irish-art-auctionbr-bidding-ends-monday-24th-january-2022/2356" 2356 /home/supmit/work/art2/morganodriscoll_2356.csv /home/supmit/work/art2/images/morganodriscoll/2356 0 0



