# -*- coding: cp1252 -*-
from finefun import *
import urllib
import subprocess
import os, sys, re, time, gzip
import csv
from tempfile import NamedTemporaryFile
import shutil
import logging
import subprocess
import io
import unidecode



# /// HISTORY/CHANGE LOG -----------------------------------------------------
# DATE            AUTHER                                    ACTION
# 2018-06-19      Saiswarup Sahu <ssahu@artinfo.com>        New version program          Ticket #
emailIdPattern = re.compile(r"\W(\w+\.?\w{0,}@\w+\.\w+\.?\w*)\W", re.MULTILINE | re.DOTALL)
absUrlPattern = re.compile(r"^https?:\/\/", re.IGNORECASE)
anchorTagPattern = re.compile(r"<a\s+[^>]{0,}href=([^\s\>]+)\s?.*?>\s*\w+", re.IGNORECASE | re.MULTILINE | re.DOTALL)
doubleQuotePattern = re.compile('"', re.MULTILINE | re.DOTALL)
htmlTagPattern = re.compile("\<\/?[^\<\>]*\/?\>", re.MULTILINE | re.DOTALL)
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
    def __init__(self, auctionId, mainUrl, downloadImages, fp):
        self.auctionId = auctionId
        self.mainUrl = mainUrl
        self.domainUrl = "https://www.lyonandturnbull.com"
        self.downloadImages = downloadImages
        self.fp = fp
        self.run()

    def run(self):
        nextPage = True
        soup = get_soup(self.mainUrl)
        self.writeHeaders(soup)  # Write the header part of csv
        try:
            total_page_nos = 5
        except:
            total_page_nos = ""
            pass
        matcatdict_en = {}
        matcatdict_fr = {}
        #with open("docs/fineart_materials.csv", newline='') as mapfile:
        with open("/root/artwork/deploydirnew/docs/fineart_materials.csv", newline='') as mapfile:
            mapreader = csv.reader(mapfile, delimiter=",", quotechar='"')
            for maprow in mapreader:
                matcatdict_en[maprow[1]] = maprow[3]
                matcatdict_fr[maprow[2]] = maprow[3]
        mapfile.close()
        lotnumberclassPattern = re.compile("lot\-number")
        colsmclassPattern = re.compile("col\-sm\-6")
        lottitleclassPattern = re.compile("lot\-title")
        subtitleclassPattern = re.compile("sub\-title")
        beginspacePattern = re.compile("^\s+")
        brPattern = re.compile("<br\s*\/?>", re.IGNORECASE)
        artistnamePattern1 = re.compile("([\w\s\.',]+)\s+\(([^\d]+)\,?\s+(\d{4})\-?(\d{0,4})\)?")
        artistnamePattern2 = re.compile("([\w\s\.'\-]+)\s+\(([^\d]+)\,?\s+(\d{4})\-?(\d{0,4})")
        artistnamePattern3 = re.compile("([\w\s\.']+)\s+\(([^\d]+)\,?\s+(\d{4})\-?(\d{0,4})")
        artistnamePattern4 = re.compile("([\w\s\.',]+)\s+\(([\d\/\w\s]+century)\s+([\w\s]+)\)", re.IGNORECASE|re.DOTALL)
        sizePattern1 = re.compile("([\d\.]+)cm\s+x\s+([\d\.]+)cm\s+x\s+([\d\.]+)(cm)")
        sizePattern2 = re.compile("([\d\.]+)cm\s+x\s+([\d\.]+)(cm)")
        datePattern = re.compile("(\d{1,2})th\s+([a-zA-Z]{3})\s+(\d{4})", re.DOTALL)
        pricesoldPattern = re.compile("Sold\s+for\s+([£$]{1})\s*([\d\.,]+)", re.IGNORECASE|re.DOTALL)
        estimatePattern = re.compile("Estimate\s*([£$]{1})\s*([\d\.,]+)\s*-\s*([\d\.,]+)", re.IGNORECASE|re.DOTALL)
        yearPattern = re.compile("(\d{4})")
        lotdetailsPattern = re.compile("lot\-details")
        next_page_urls = [self.mainUrl +"&pn="+ str(x) for x in range(1, total_page_nos + 1)]
        for page_url in next_page_urls:
            soup = get_soup(page_url)
            productDetails = soup.findAll('div',{'class':'auction-lot-image'})
            for product in productDetails:
                auction_house_name = "Lyon & Turnbull"
                auction_location = "Edinburgh"
                auction_num = self.auctionId
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
                artist_nationality = ""
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

                if aTag:
                    detailPageUrl = 'https://www.lyonandturnbull.com'+aTag["href"]
                    try:
                        lot_origin_url=detailPageUrl
                        print(lot_origin_url)
                        print('____________________________')
                    except:
                        pass
                    detailPageSoup = get_soup(detailPageUrl)
                    try:
                        lot_details = detailPageSoup.find('span',{'class',lotnumberclassPattern}).getText().replace('\t','')
                        lot_num=''.join(re.findall('Lot\s(\d+.*?)',lot_details)).strip()
                    except:
                        pass
                    artist_name_data = ""
                    try:
                        artist_name_data = detailPageSoup.find_all('h1', {'class': lottitleclassPattern})[0].renderContents().decode('utf-8')
                        artist_name_data = re.split(brPattern, artist_name_data)[0]
                        artist_name_data = htmlTagPattern.sub("", artist_name_data)
                        artist_name_data = artist_name_data.replace("\n", "").replace("\r", "")
                        nps1 = re.search(artistnamePattern1, artist_name_data)
                        nps2 = re.search(artistnamePattern2, artist_name_data)
                        nps3 = re.search(artistnamePattern3, artist_name_data)
                        nps4 = re.search(artistnamePattern4, artist_name_data)
                        if nps1 and artist_name == "":
                            artist_name = nps1.groups()[0]
                            artist_name = beginspacePattern.sub("", artist_name)
                            artist_nationality = nps1.groups()[1]
                            artist_birth = nps1.groups()[2]
                            artist_death = nps1.groups()[3]
                        elif nps2 and artist_name == "":
                            artist_name = nps2.groups()[0]
                            artist_name = beginspacePattern.sub("", artist_name)
                            artist_nationality = nps2.groups()[1]
                            artist_birth = nps2.groups()[2]
                            artist_death = nps2.groups()[3]
                        elif nps3 and artist_name == "":
                            artist_name = nps3.groups()[0]
                            artist_name = beginspacePattern.sub("", artist_name)
                            artist_nationality = nps3.groups()[1]
                            artist_birth = nps3.groups()[2]
                            artist_death = nps3.groups()[3]
                        elif nps4 and artist_name == "":
                            artist_name = nps4.groups()[0]
                            artist_name = beginspacePattern.sub("", artist_name)
                            artist_nationality = nps4.groups()[2]
                            artist_birth = nps4.groups()[1]
                            artist_death = ""
                        elif artist_name == "":
                            artist_name = artist_name_data
                            artist_nationality = ""
                            artist_birth = ""
                            artist_death = ""
                    except:
                        pass
                    auctionnameh2tags = detailPageSoup.find_all("h2")
                    if auctionnameh2tags.__len__() > 0:
                        auction_name = auctionnameh2tags[0].renderContents().decode('utf-8')
                        auction_name = htmlTagPattern.sub("", auction_name)
                        auction_name = auction_name.replace("\n", "").replace("\r", "")
                    auction_name = auction_name.replace("&amp;", "&").replace("&nbsp;", " ")
                    auctiondateh3tags = detailPageSoup.find_all("h3")
                    auction_date = ""
                    if auctiondateh3tags.__len__() > 0:
                        auctiondatecontents = auctiondateh3tags[0].renderContents().decode('utf-8')
                        auctiondatecontents = auctiondatecontents.replace("\n", "").replace("\r", "")
                        dps = re.search(datePattern, auctiondatecontents)
                        if dps:
                            dd = dps.groups()[0]
                            mon = dps.groups()[1]
                            yyyy = dps.groups()[2]
                            auction_date = str(dd) + "-" + mon + "-" + str(yyyy)[2:]
                    auction_start_date = auction_date
                    artworkspantag = detailPageSoup.find("span", {'class' : subtitleclassPattern})
                    if artworkspantag is not None:
                        artwork_name = artworkspantag.renderContents().decode('utf-8')
                        artwork_name = beginspacePattern.sub("", artwork_name)
                    try:
                        if artist_name=='':
                            data_flow=All_Data = detailPageSoup.findAll('div', {'class': colsmclassPattern})[1].findAll('p')[1].getText(separator=u'@').strip().replace('@@@', '@').replace('@@', '@').split("@")
                            print(data_flow)
                            artist_name = data_flow[1]
                            artwork_name = data_flow[2]
                    except:
                        pass
                    yps = re.search(yearPattern, artwork_name)
                    if yps:
                        artwork_start_year = yps.groups()[0]
                    try:
                        All_Data = detailPageSoup.findAll('div', {'class': 'lot-desc'})[0].getText(separator=u'@').strip().replace('@@@', '@').replace('@@', '@').split("@")
                        #print(All_Data)
                    except:
                        pass
                    try:
                        artwork_materials = getMaterial(All_Data)
                    except:
                        pass
                    try:
                        artwork_markings = getSignature(All_Data)
                        if artwork_materials=='':
                            artwork_materials=getMaterial(artwork_markings.split(','))
                            artwork_markings=artwork_markings.replace(artwork_materials,'').replace(',','').strip()
                    except:
                        pass
                    try:
                        artwork_condition_in=getCondition(All_Data)
                    except:
                        pass
                    artwork_measureunit = ""
                    for d in All_Data:
                        zps1 = re.search(sizePattern1, d)
                        zps2 = re.search(sizePattern2, d)
                        if zps1:
                            artwork_measurements_height = zps1.groups()[0]
                            artwork_measurements_width = zps1.groups()[1]
                            artwork_measurements_depth = zps1.groups()[2]
                            artwork_measureunit = zps1.groups()[3]
                            auction_measureunit = artwork_measureunit
                            break
                        elif zps2:
                            artwork_measurements_height = zps2.groups()[0]
                            artwork_measurements_width = zps2.groups()[1]
                            artwork_measureunit = zps2.groups()[2]
                            auction_measureunit = artwork_measureunit
                            break
                    artwork_size_notes = str(artwork_measurements_height) + " x " + str(artwork_measurements_width)
                    if artwork_measurements_depth != "0":
                        artwork_size_notes += " x " + str(artwork_measurements_depth)
                    artwork_size_notes += " " + artwork_measureunit
                    processedArtworkName = artwork_name.replace(" ", "_")
                    try:
                        artwork_images1 = detailPageSoup.find('div',{'class':'lot-gallery-wrapper pull-left'}).findAll('img')[0]['src'].replace('small','medium')
                        processedArtistName = artist_name.replace(" ", "_")
                        processedArtistName = unidecode.unidecode(processedArtistName)
                        image1_name = self.auctionId + "__" + processedArtistName + "__" + str(lot_num) + "_a.jpg"
                    except:
                        pass
                    try:
                        artwork_images2 = detailPageSoup.find('div',{'class':'lot-gallery-wrapper pull-left'}).findAll('img')[1]['src'].replace('small','medium')
                        processedArtistName = artist_name.replace(" ", "_")
                        processedArtistName = unidecode.unidecode(processedArtistName)
                        image2_name = self.auctionId + "__" + processedArtistName + "__" + str(lot_num) + "_b.jpg"
                    except:
                        pass
                    try:
                        artwork_images3 = detailPageSoup.find('div',{'class':'lot-gallery-wrapper pull-left'}).findAll('img')[2]['src'].replace('small','medium')
                        processedArtistName = artist_name.replace(" ", "_")
                        processedArtistName = unidecode.unidecode(processedArtistName)
                        image3_name = self.auctionId + "__" + processedArtistName + "__" + str(lot_num) + "_c.jpg"
                    except:
                        pass
                    price_sold_strong_tags = detailPageSoup.find_all("strong")
                    for strongtag in price_sold_strong_tags:
                        strongcontents = strongtag.renderContents().decode('utf-8')
                        psp = re.search(pricesoldPattern, strongcontents)
                        if psp:
                            price_sold = psp.groups()[1]
                            if "£" in str(psp.groups()[0]):
                                price_sold = price_sold + " GBP"
                            elif "$" in str(psp.groups()[0]):
                                price_sold = price_sold + " USD"
                    estimatedivtags = detailPageSoup.find_all("div", {'class' : 'estimate'})
                    if estimatedivtags.__len__() > 0:
                        estimatecontents = estimatedivtags[0].renderContents().decode('utf-8')
                        estimatecontents = htmlTagPattern.sub("", estimatecontents)
                        estimatecontents = estimatecontents.replace("\n", "").replace("\r", "")
                        eps = re.search(estimatePattern, estimatecontents)
                        if eps:
                            currency = eps.groups()[0]
                            price_estimate_min = eps.groups()[1]
                            price_estimate_max = eps.groups()[2]
                    try:
                        if len(All_Data) > 1:
                            estimation = [x for x in All_Data if "Estimate" in x.strip()]
                            if estimation.__len__() != 0:
                                estimation = estimation[0]
                               # print(estimation)
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
                        if len(All_Data) > 1:
                            priceRealized = [x for x in All_Data if "Sold" in x.strip()]
                            priceRealized = priceRealized[0]
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
                    # try:
                    #     artist_name=re.sub("\s[A-z].[A-Z].*","",artist_name)
                    # except:
                    #     pass
                    if not detailPageSoup or detailPageSoup is None:
                        continue
                    h2tags = detailPageSoup.find_all("h2")
                    if h2tags.__len__() > 0:
                        titleanchor = h2tags[0].find('a')
                        if titleanchor is not None:
                            auction_name=titleanchor.renderContents().decode('utf-8')
                    day=''.join(re.findall("\d+",auction_date.split(' ')[0]))
                    try:
                        auction_start_date=day+'-'+auction_date.split(' ')[1][:3]+'-'+auction_date.split(' ')[-1][-2:]
                    except:
                        auction_start_date=""
                    descdivtags = detailPageSoup.find_all("div", {'class' : 'lot-desc'})
                    if descdivtags.__len__() > 0:
                        desccontents = descdivtags[0].renderContents().decode('utf-8')
                        desccontents = htmlTagPattern.sub("", desccontents)
                        desccontents = desccontents.replace("\n", " ").replace("\r", " ")
                        artwork_description = "<strong><br>Description:</strong><br>Artist: %s<br/>Title: %s<br/>"%(artist_name, artwork_name) + desccontents
                    try:
                        artwork_description=artwork_description.replace('Provenance', '<Strong><br>Provenance</strong><br>').replace('Exhibited', '<br><strong>Exhibited</strong><br>').replace('Note', '<Strong><br>Note</strong><br>')
                        artwork_description = artwork_description.replace("Download lot details PDF","").replace("Back to list","").replace("Next lot","").replace("Previous lot","").replace("\n","").strip()
                    except:
                        pass
                    #print(detailPageSoup.findAll('div', {'class': 'col-sm-6'})[1].getText(separator=u' '))
                    try:
                        artwork_start_year, artwork_end_year = getStartEndYear(artwork_name)
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
                            if artwork_materials_data.lower() == "colour":
                                artwork_category = "Paintings"
                            if artwork_materials_data.lower() == "woodcut":
                                artwork_category = "Paintings"
                            if artwork_materials_data.lower() == "silver":
                                artwork_category = "Photographs"
                            if artwork_materials_data.lower() == "watercolour":
                                artwork_category = "Miniatures"
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
                            if artwork_materials_data.lower() == "colour":
                                artwork_category = "Paintings"
                            if artwork_materials_data.lower() == "woodcut":
                                artwork_category = "Paintings"
                            if artwork_materials_data.lower() == "synthetic":
                                artwork_category = "Paintings"
                            if artwork_materials_data.lower() == "silver":
                                artwork_category = "Photographs"
                            if artwork_materials_data.lower() == "watercolour":
                                artwork_category = "Miniatures"
                    except:
                        pass
                    price_estimate_min = price_estimate_min.replace(",", "").replace(" ", "")
                    price_estimate_max = price_estimate_max.replace(",", "").replace(" ", "")
                    price_sold = price_sold.replace(",", "").replace(" ", "")
                    if artwork_images1=='':
                        processedArtworkName = artwork_name.replace(" ", "_")
                        artwork_images1=detailPageSoup.find('div',{'class':'image-wrapper text-center'}).find('img')['src']
                        image1_name = self.auctionId + "__" + processedArtistName + "__" + str(lot_num) + "_a.jpg"
                    try:
                        rX = lambda x: " ".join(x.replace(",", "").replace("\n", "").replace("\t", "").replace('"', "").splitlines())
                        self.fp.write('"' + 
                            rX(auction_house_name) + '","' + rX(auction_location) + '","' + rX(auction_num) + '","' + rX(
                                auction_start_date) + '","' + rX(auction_end_date) + '","'+rX(auction_name)+'","'
                            + rX(lot_num) + '","' + rX(sublot_num) + '","' + rX(price_kind) + '","' + rX(
                                price_estimate_min) + '","' + rX(price_estimate_max) + '","' + rX(price_sold) + '","' + rX(
                                artist_name.strip().title()) + '","'
                            + rX(artist_birth) + '","' + rX(artish_death) + '","' + rX(artist_nationality) + '","' + rX(
                                artwork_name.strip().title()) + '","' +
                            rX(artwork_year_identifier) + '","' + rX(artwork_start_year) + '","' + rX(
                                artwork_end_year) + '","' + rX(
                                artwork_materials) + '","' + rX(artwork_category) + '","' + rX(artwork_markings) + '","'
                            + rX(artwork_edition) + '","' + rX(artwork_description) + '","' + rX(
                                artwork_measurements_height) + '","' + rX(artwork_measurements_width) + '","' + rX(
                                artwork_measurements_depth) + '","' +
                            rX(artwork_size_notes) + '","' + rX(auction_measureunit) + '","' + rX(
                                artwork_condition_in) + '","' + rX(
                                artwork_provenance) + '","' + rX(artwork_exhibited) + '","' + rX(artwork_literature) + '","' +
                            rX(artwork_images1) + '","' + rX(artwork_images2) + '","' + rX(artwork_images3) + '","' + rX(
                                artwork_images4) + '","' + rX(artwork_images5) + '","' +
                            rX(image1_name) + '","' + rX(image2_name) + '","' + rX(image3_name) + '","' + rX(
                                image4_name) + '","' + rX(
                                image5_name) + '","' + rX(lot_origin_url) + '"\n')
                    except:
                        print("Error: %s"%sys.exc_info()[1].__str__())





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
    pageurl = "http://216.137.189.57:8080/scrapers/finish/?scrapername=LyonandTurnbull&auctionnumber=%s&auctionurl=%s&scrapertype=2"%(auctionno, urllib.parse.quote(auctionurl))
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
    Scrape(auctionnumber, auctionurl, downloadimages,  fp)
    fp.close()
    updatestatus(auctionnumber, auctionurl)


# Example: python lyonandturnbull.py "https://www.lyonandturnbull.com/auction/search/?au=9214&sd=2" 9214 /home/supmit/work/art2/lyonandturnbull_9214.csv /home/supmit/work/art2/images/lyonandturnbull/9214 0 0

