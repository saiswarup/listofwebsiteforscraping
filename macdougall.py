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

def get_soup_local(pageUrl, httpHeaders = {}):
    #gc.collect()
    httpHeaders['Cookie'] = ""
    httpHeaders['Referer'] = "https://macdougallauction.com/en/catalogue/35"
    httpHeaders['Pragma'] = "no-cache"
    httpHeaders['Cache-Control'] = "no-cache"
    httpHeaders['Host'] = "macdougallauction.com"
    httpHeaders['Sec-Fetch-Dest'] = "document"
    httpHeaders['Sec-Fetch-Mode'] = "navigate"
    httpHeaders['Sec-Fetch-Site'] = "same-origin"
    httpHeaders['Sec-Fetch-User'] = "?1"
    httpHeaders['Connection'] = "keep-alive"
    httpHeaders['Alt-Used'] = "macdougallauction.com"
    httpHeaders['User-Agent'] = "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:97.0) Gecko/20100101 Firefox/97.0"
    #print("PAGE URL: %s"%pageUrl)
    pageRequest = urllib.request.Request(pageUrl, None, httpHeaders)
    try:
        pageResponse = opener.open(pageRequest)
        headers = pageResponse.info()
        while 'Location' in headers.keys():
            requestUrl = headers["Location"]
            print(requestUrl)
            if requestUrl == "/home.html":
                requestUrl = pageUrl+"home.html/"
            else:
                requestUrl = requestUrl
            pageRequest = urllib.request.Request(requestUrl, None, httpHeaders)
            try:
                pageResponse = opener.open(pageRequest)
                headers = pageResponse.info()
            except:
                break
    except:
        pageResponse = None
        print("Error in get_soup_local: %s"%sys.exc_info()[1].__str__())
        return pageResponse

    if pageResponse is None:
        return None
    else:
        pageContent = decodeGzippedContent(pageResponse.read())
        #print(pageContent)
        pageSoup = BeautifulSoup(pageContent, features="html.parser")
        #gc.collect()
        return pageSoup
###########################################################################################

def getDimaisionLocal(dim):
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
        self.domainUrl = "https://macdougallauction.com"
        self.imagedir = imagedir
        self.downloadImages = downloadImages
        self.scrapperName = scrapperName
        self.fp = fp
        self.run(auctionId, csvpath, self.imagedir)

    

    def run(self, auctionId, csvpath, imagedir):
        nextPage = True
        soup = get_soup_local(self.mainUrl)
        self.writeHeaders(soup)  # Write the header part of csv
        try:
            total_page_nos = 30
        except:
            total_page_nos = ""
            pass
        try:
            next_page_urls = [mainUrl + "?page=" + str(x) for x in range(1, total_page_nos + 1)]
            #print(next_page_urls)
        except:
            next_page_urls = ""
            pass
        last_lot_no = "-1"
        for page_url in next_page_urls:
            soup = get_soup_local(page_url)
            productDetails = soup.findAll('a',{'class':'asset'})
            for product in productDetails:
                auction_house_name = "MacDougall"
                auction_location = "London"
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

                try:
                    aTag = product
                except:
                    aTag = None
                    pass
                if aTag:
                    detailPageUrl = 'https://macdougallauction.com'+aTag["href"]
                    try:
                        lot_origin_url=detailPageUrl
                    except:
                        pass
                    detailPageSoup = get_soup_local(detailPageUrl)
                    print('___________________________')
                    try:
                        artist_name=detailPageSoup.find('h3',{'class':'mt-5'}).getText()
                    except:
                        pass
                    try:
                        years = re.findall("\d{4}", artist_name)
                        artist_birth, artish_death = ['', '']
                        if len(years) > 1:
                             artist_birth = years[0]
                             artish_death = years[1]
                        elif len(years) == 1:
                            artist_birth = years[0]
                    except:
                        pass
                    try:
                        artist_name=re.sub('[(].*','',artist_name.strip())
                    except:
                        pass

                    if '.' in artist_name:
                        artist_name_lot=artist_name.split('.')[1]
                        lot_num=''.join(re.findall("\d+", artist_name.split('.')[0]))
                        artist_name=artist_name_lot.strip().title()
                    try:
                        lot_num, sublot_num = getSubLot(lot_num)

                    except:
                        pass
                    print(lot_num)
                    try:
                        artwork_name = detailPageSoup.find('p',{'class':'mt-3'}).find('i').getText()
                    except:
                        pass
                    try:
                        artwork_start_year, artwork_end_year = getStartEndYear(artwork_name)
                    except:
                        pass
                    All_Data = detailPageSoup.find('p',{'class':'mt-3'}).getText(separator=u'@').strip().replace('@@@', '@').replace('@@', '@').replace('\n','@').replace('        ','').replace(',','@')
                    All_Data = All_Data.split('@')
                    setData = detailPageSoup.find('p', {'class': 'mt-3'}).getText(separator=u'@').strip().replace(
                        '@@@', '@').replace('@@', '@').replace('\n', '@').replace('        ', '').split('@')
                    try:
                        artwork_materials = getMaterial(All_Data)
                    except:
                        pass
                    try:
                        artwork_markings = getSignature(All_Data)
                    except:
                        pass
                    try:
                        if len(All_Data) > 1:
                            estimation = [x for x in setData if "GBP" in x.strip() or "pounds" in x.strip()]
                            if estimation.__len__() != 0:
                                estimation = str(estimation[0]).replace(',','')
                                priceList=re.findall("\d+",estimation)
                                if priceList.__len__() == 2:
                                    price_estimate_min = ''.join(re.findall("\d+", X(priceList[0].strip())))
                                    price_estimate_max = ''.join(re.findall("\d+", X(priceList[1].strip())))
                                if priceList.__len__() == 1:
                                    price_estimate_min = ''.join(re.findall("\d+", X(priceList[0].strip())))
                                    price_estimate_max = "0"
                    except:
                        pass
                    if price_estimate_min=='':
                        estimation=detailPageSoup.find('p',{'class':'mt-3'}).find('b').getText()
                        if estimation.__len__() != 0:
                            estimation = str(estimation).replace(',', '')
                            priceList = re.findall("\d+", estimation)
                            if priceList.__len__() == 2:
                                price_estimate_min = ''.join(re.findall("\d+", X(priceList[0].strip())))
                                price_estimate_max = ''.join(re.findall("\d+", X(priceList[1].strip())))
                            if priceList.__len__() == 1:
                                price_estimate_min = ''.join(re.findall("\d+", X(priceList[0].strip())))
                                price_estimate_max = "0"

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

                    if auction_num=='':
                        auction_num=auctionId
                    try:
                        dim_list = [x for x in All_Data if " cm" in x]
                        if dim_list.__len__() > 1:
                            dim_data = " x ".join(dim_list)
                        elif dim_list.__len__() == 1:
                            dim_data = dim_list[0]
                        else:
                            dim_data = ""
                        if "(" in dim_data:
                            dim_data = dim_data.split("(")[0]
                        dimaisionList = getDimaisionLocal(dim_data)
                        artwork_measurements_height = dimaisionList[0].replace("1.9", "19.").replace(".9", "9.")
                        artwork_measurements_width = dimaisionList[1].replace("1.9", "19.").replace(".9", "9.")
                        artwork_size_notes = artwork_measurements_height + "x" + artwork_measurements_width + "x" + artwork_measurements_depth + ' ' + 'cm'
                    except:
                        artwork_size_notes, artwork_measurements_height, artwork_measurements_width, artwork_measurements_depth = "0", "0", "0", "0"
                        pass
                    auction_measureunit = 'cm'
                    try:
                        artwork_images1 = 'https://macdougallauction.com'+detailPageSoup.find("img", {"class": "img-fluid"})['src']
                        #image1_name = scrapperName+'-'+auction_location+'-'+auction_start_date+'-'+auctionId+'-'+lot_num +'-'+price_estimate_min+'-a'+'.jpg'
                        processedArtistName = artist_name.replace(" ", "_")
                        processedArtistName = unidecode.unidecode(processedArtistName)
                        image1_name = auctionId + "__" + processedArtistName + "__" + str(lot_num) + "_a.jpg"
                    except:
                        pass

                    try:
                        auction_name=detailPageSoup.find('div',{'class':'asset-view'}).find('h2').getText().replace('Catalogue:','').strip()
                    except:
                        pass
                    try:
                        date = detailPageSoup.find('div',{'class':'asset-view'}).find('p').getText()
                        date_data = date.replace(',', '').split(' ')
                        date = date_data[0]
                        months = date_data[1]
                        year = date_data[-1][-2:]
                        auction_start_date = date + '-' + months + '-' + year
                    except:
                        pass
                    try:
                        image1_name="".join(image1_name.split())
                        image2_name="".join(image2_name.split())
                        image3_name="".join(image3_name.split())
                        image4_name="".join(image4_name.split())
                        image5_name="".join(image5_name.split())
                    except:
                        pass
                    #

                    details_1,details_2,details_3='','',''
                    details = detailPageSoup.find('div',{'class':'asset-view'})
                    details_1=details.find('h3',{'class':'mt-5'}).getText()
                    details_2=detailPageSoup.findAll('p',{'class':'mt-3'})[0].getText()
                    try:
                        details_3 = detailPageSoup.findAll('p', {'class': 'mt-3'})[1].getText()
                    except:
                        pass
                    artwork_description = "<strong><br>Description:</strong><br>" +' '+details_1+' '+details_2+' '+details_3
                    artwork_description=artwork_description.replace('Exhibited:','<Strong><br>Exhibited:</strong><br>').replace('Provenance:','<Strong><br>Provenance:</strong><br>').replace('Literature:','<Strong><br>Literature:</strong><br>')


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
                        if artwork_category == '':
                            artwork_materials_data = artwork_materials.strip().replace('\t', '').split(' ')[0]
                            #print(artwork_materials_data), 'saisidididhdihdihd'
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
                    artwork_markings = artwork_markings.replace('"', "").replace("'", "").replace(";", " ").replace(",", " ")
                    artwork_edition = str(artwork_edition)
                    artwork_description = str(artwork_description)
                    artwork_description = artwork_description.replace('"', "").replace("'", "").replace(";", " ").replace(",", " ")
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
                    artist_name=re.sub('\d.*','',artist_name)
                    artist_name = re.sub('\sB\s', '', artist_name)
                    artist_name=artist_name.replace('\n','').replace(' B ','').replace(' b ','')
                    print(artist_name)

                    try:
                        rX = lambda x: " ".join(
                                x.replace(",", "").replace("\n", "").replace("\t", "").replace('"', "").splitlines())
                        self.fp.write(
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
            if int(lot_num) <= int(last_lot_no):
                break
            last_lot_no = str(lot_num)


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
    pageurl = "http://216.137.189.57:8080/scrapers/finish/?scrapername=Macdougall&auctionnumber=%s&auctionurl=%s&scrapertype=2"%(auctionno, urllib.parse.quote(auctionurl))
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
    scrapperName = "Doyle"
    downloadImages = True
    if sys.argv.__len__() > 2 and sys.argv[2] == "True":
        downloadImages = "True"
    fp = open(csvpath, "w")
    Scrape(mainUrl, auctionId, csvpath, imagedir, downloadImages, scrapperName,  fp)
    fp.close()
    updatestatus(auctionId, mainUrl)

# Example: python macdougall.py "https://macdougallauction.com/en/catalogue/35" 35 /home/supmit/work/art2/macdougall_35.csv /home/supmit/work/art2/images/macdougall/35 0 0



