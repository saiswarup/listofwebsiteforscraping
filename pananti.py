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
import urllib
from urllib.parse import urlencode, quote_plus
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
    def __init__(self, auctionUrl, auctionId, csvpath, imagedir, downloadImages, scrapperName, fp):
        self.auctionId = auctionId
        self.mainUrl = auctionUrl
        self.domainUrl = "https://www.pananti.com"
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


    def _getCookieFromResponse(cls, lastHttpResponse):
        if not lastHttpResponse:
            return ""
        cookies = ""
        responseCookies = lastHttpResponse.getheader("Set-Cookie")
        pathPattern = re.compile(r"Path=/;", re.IGNORECASE)
        domainPattern = re.compile(r"Domain=[^;,]+(;|,)", re.IGNORECASE)
        expiresPattern = re.compile(r"Expires=[^;]+;", re.IGNORECASE)
        maxagePattern = re.compile(r"Max-Age=[^;]+;", re.IGNORECASE)
        samesitePattern = re.compile(r"SameSite=[^;]+;", re.IGNORECASE)
        securePattern = re.compile(r"secure;?", re.IGNORECASE)
        httponlyPattern = re.compile(r"HttpOnly;?", re.IGNORECASE)
        if responseCookies and responseCookies.__len__() > 1:
            cookieParts = responseCookies.split("Path=/")
            for i in range(cookieParts.__len__()):
                cookieParts[i] = re.sub(domainPattern, "", cookieParts[i])
                cookieParts[i] = re.sub(expiresPattern, "", cookieParts[i])
                cookieParts[i] = re.sub(maxagePattern, "", cookieParts[i])
                cookieParts[i] = re.sub(samesitePattern, "", cookieParts[i])
                cookieParts[i] = re.sub(securePattern, "", cookieParts[i])
                cookieParts[i] = re.sub(pathPattern, "", cookieParts[i])
                cookieParts[i] = re.sub(httponlyPattern, "", cookieParts[i])
                cookieParts[i] = cookieParts[i].replace(",", "")
                cookieParts[i] = re.sub(re.compile("\s+", re.DOTALL), "", cookieParts[i])
                cookies += cookieParts[i]
        cookies = cookies.replace(";;", ";")
        return(cookies)

    _getCookieFromResponse = classmethod(_getCookieFromResponse)

    def _decodeGzippedContent(cls, encoded_content):
        response_stream = io.BytesIO(encoded_content)
        decoded_content = ""
        try:
            gzipper = gzip.GzipFile(fileobj=response_stream)
            decoded_content = gzipper.read()
        except: # Maybe this isn't gzipped content after all....
            decoded_content = encoded_content
        decoded_content = decoded_content.decode('utf-8')
        return(decoded_content)

    _decodeGzippedContent = classmethod(_decodeGzippedContent)


    def dologin(self, username, password):
        self.sessionCookies = ""
        self.httpHeaders = { 'User-Agent' : r'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36',  'Accept' : 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8', 'Accept-Language' : 'en-us,en;q=0.5', 'Accept-Encoding' : 'gzip,deflate', 'Accept-Charset' : 'ISO-8859-1,utf-8;q=0.7,*;q=0.7', 'Connection' : 'keep-alive', }
        self.httpHeaders['Pragma'] = "no-cache"
        self.httpHeaders['Cache-Control'] = "no-cache"
        self.httpHeaders['Host'] = "www.pananti.com"
        self.httpHeaders['Referer'] = "https://www.pananti.com/uk/my-panel/index.asp"
        self.httpHeaders['Origin'] = "https://www.pananti.com"
        self.httpHeaders['upgrade-insecure-requests'] = "1"
        self.httpHeaders['sec-fetch-dest'] = "document"
        self.httpHeaders['sec-fetch-mode'] = "navigate"
        self.httpHeaders['sec-fetch-site'] = "same-origin"
        self.httpHeaders['sec-fetch-user'] = "?1"
        self.httpHeaders['Content-Type'] = "application/x-www-form-urlencoded"
        self.httpHeaders['Cookie'] = "acceptCookies=true; registrazione%5FGalleria+Pananti+Casa+d%27Aste=attivato=1&pagineVis=3; ASPSESSIONIDSUBDBBCB=IHDFHCOAOJAPMBONJCAIDOMJ; ASPSESSIONIDSWCCCBCA=OKGFPJCBBDCIBODMMNHBBJKA; codiceutente%5FGalleria+Pananti+Casa+d%27Aste=I2UhyTEbzDVtFTUfBD50zHYWBCMsRTJmJCM0AGRcNqNb; _custom_data_username=Mitra%20Supriyo; _custom_data_email=supriyom%40theeolico.com;"
        self.requestUrl = "https://www.pananti.com/uk/controller.asp?action=community-login"
        data = {'usr' : "supriyom@theeolico.com", 'psw' : "xtmt365i", 'remember' : "checked", 'send' : "Enter", 'formName' : "userConsole", 'spedizione' : "", 'pagamento' : "", '_success' : 'https://www.pananti.com/uk/auction-2098/natura-morta-76543?rnd=725307&rnd=981472'}
        self.postdata = urlencode(data).encode('utf-8')
        self.httpHeaders['Content-Length'] = self.postdata.__len__()
        self.opener = urllib.request.build_opener(urllib.request.HTTPHandler(), urllib.request.HTTPSHandler())
        self.pageRequest = urllib.request.Request(self.requestUrl, data=self.postdata, headers=self.httpHeaders)
        self.pageResponse = None
        try:
            self.pageResponse = self.opener.open(self.pageRequest)
            headers = self.pageResponse.getheaders()
            #print(headers)
            if "Location" in headers:
                self.requestUrl = headers["Location"]
                self.pageRequest = urllib.request.Request(self.requestUrl, headers=self.httpHeaders)
                try:
                    self.pageResponse = self.no_redirect_opener.open(self.pageRequest)
                except:
                    print ("Couldn't fetch page due to limited connectivity. Please check your internet connection and try again. %s"%sys.exc_info()[1].__str__())
                    sys.exit()
        except:
            print ("Couldn't fetch page due to limited connectivity. Please check your internet connection and try again. %s"%sys.exc_info()[1].__str__())
        #self.httpHeaders["Referer"] = self.requestUrl
        self.sessionCookies = self.__class__._getCookieFromResponse(self.pageResponse)
        self.httpHeaders["Cookie"] = "acceptCookies=true; registrazione%5FGalleria+Pananti+Casa+d%27Aste=attivato=1&pagineVis=3; ASPSESSIONIDSUBDBBCB=IHDFHCOAOJAPMBONJCAIDOMJ; ASPSESSIONIDSWCCCBCA=OKGFPJCBBDCIBODMMNHBBJKA;" + self.sessionCookies
        #print(self.httpHeaders["Cookie"])
        self.currentPageContent = self.__class__._decodeGzippedContent(self.pageResponse.read())
        #print(self.currentPageContent)


    def run(self, auctionId, csvpath, imagedir):
        nextPage = True
        print("Trying to login... ")
        self.dologin("supriyom@theeolico.com", "xtmt365i")
        print("Successfully logged in. Now trying to get %s"%self.mainUrl)
        del self.httpHeaders['Content-Length']
        #print(self.httpHeaders)
        soup = get_soup(self.mainUrl, httpHeaders=self.httpHeaders)
        print("Collected soup, writing headers now...")
        self.writeHeaders(soup)  # Write the header part of csv
        try:
            total_page_nos = 10
        except:
            total_page_nos = ""
            pass
        try:
            next_page_urls = [auctionUrl + "?pag=" + str(x) for x in range(1, total_page_nos + 1)]
            #print(next_page_urls)
        except:
            next_page_urls = ""
            pass
        for page_url in next_page_urls:
            soup = get_soup(page_url, httpHeaders=self.httpHeaders)
            productDetails = soup.findAll('div', {'class': 'lotItemList'})
            #print(len(productDetails))
            try:
                auction_name = soup.find('div', {'id': 'panelTitlePage'}).renderContents().decode('utf-8')
                auction_name = htmlTagPattern.sub("", auction_name)
                auction_name = auction_name.replace("\n", "").replace("\r", "")
            except:
                auction_name = ""
            #print("Auction Title: %s"%auction_name)
            try:
                auction_start_date = soup.find("div", {'class' : 'data d-block mb-4'}).renderContents().decode('utf-8')
            except:
                auction_start_date = ""
            for product in productDetails:
                auction_house_name = "Galleria Pananti"
                auction_location = "Florence"
                auction_num = ""
                #auction_start_date = ""
                auction_end_date = ""
                #auction_name=''
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

                print('__________________________________')
                try:
                    lot_num = product.find("div", {"class": "number"}).getText()
                    lot_num = lot_num.strip()
                    print("lotNum:- %s"%lot_num)
                except:
                    print("Error1: %s"%sys.exc_info()[1].__str__())
                try:
                    lot_num, sublot_num = getSubLot(lot_num)
                except:
                    print("Error2: %s"%sys.exc_info()[1].__str__())
                try:
                    artist_name = product.find('div', {'class': 'title'}).find('h3').getText()
                    artist_name = artist_name.strip()
                    #print("artist_name:- %s"%artist_name)
                except:
                    print("Error3: %s"%sys.exc_info()[1].__str__())
                try:
                    artwork_name = product.find('div', {'class': 'titleOpera'}).getText()
                    artwork_name = artwork_name.strip()
                    #print("artwork_name:- %s"%artwork_name)
                except:
                    print("Error4: %s"%sys.exc_info()[1].__str__())
                try:
                    artist_birth, artish_death = getStartEndYear(artist_name)
                except:
                    pass
                try:
                    artwork_start_year,artwork_end_year=getStartEndYear(artwork_name)
                except:
                    pass
                try:
                    details=product.find('div',{'class':'desc'}).getText().split(',')
                    #print(details)
                except:
                    print("Error5: %s"%sys.exc_info()[1].__str__())
                try:
                    artist_nationallity = product.find('div', {'class': 'luogoAutore'}).getText().strip()
                    if artist_birth=='':
                        artist_birth, artish_death = getStartEndYear(artist_nationallity)
                    #print(artist_nationallity)
                    if ',' in artist_nationallity:
                        #print(artist_nationallity)
                        artist_nationallity=artist_nationallity.split(',')[0]
                        #print(artist_nationallity)
                        artist_nationallity =  ''.join(re.findall('[A-Za-z]',artist_nationallity))
                    #print(artist_nationallity)
                except:
                    print("Error3: %s"%sys.exc_info()[1].__str__())
                try:
                    artwork_materials = getMaterial(details)
                    artwork_materials = artwork_materials.replace('"', "").replace("'", "")
                except:
                    pass

                try:
                    artwork_markings = getSignature(details)
                    artwork_markings = artwork_markings.replace('"', "").replace("'", "").replace(";", " ").replace(",", " ")
                except:
                    pass
                try:
                    dimension = [x for x in details if "cm." in x.strip().lower()]
                    # print(dimension)
                    dimension = dimension[0].replace(',', '.').replace("in.", "").strip().replace('-', ' ')
                    dimension = re.sub("cm.", "", dimension)
                    # print(dimension)
                    auction_measureunit = 'cm'
                    dimaisionList = getDimaision(dimension)
                    artwork_measurements_height = dimaisionList[0].replace("1.9", "19.").replace(".9", "9.")
                    artwork_measurements_width = dimaisionList[1].replace("1.9", "19.").replace(".9", "9.")
                    artwork_measurements_depth = dimaisionList[2].replace("1.9", "19.").replace(".9", "9.")
                except:
                    pass
                try:
                    artwork_size_notes = artwork_measurements_height + 'x' + artwork_measurements_width + " " + 'cm'
                except:
                    pass
                if artwork_measurements_height=='':
                    artwork_size_notes=''
                try:
                    estimation = product.find('div', {'class': 'estimate2'}).getText().strip()
                    priceList = estimation.replace("EUR", "").replace(',', '').replace('.', '').strip().split("/")
                    if priceList.__len__() == 2:
                        price_estimate_min = ''.join(re.findall("\d+", X(priceList[0].strip())))
                        price_estimate_max = ''.join(re.findall("\d+", X(priceList[1].strip())))
                    if priceList.__len__() == 1:
                        price_estimate_min = ''.join(re.findall("\d+", X(priceList[0].strip())))
                        price_estimate_max = "0"
                except:
                    price_estimate_min = ""
                    price_estimate_max = ""
                    print("Error: %s"%sys.exc_info()[1].__str__())
                #print("Prices: %s / %s"%(price_estimate_min, price_estimate_max))
                try:
                    priceRealized = product.find('div', {'class': 'statoLottoBox'}).getText().strip()
                    price_sold = ''.join(re.findall("\d+", priceRealized.strip()))
                    #print("Sold Price = " + price_sold)
                except:
                    print("Error6: %s"%sys.exc_info()[1].__str__())
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
                """
                try:
                    auction_name=soup.find('div', {'class': 'itemListTitle Prev'}).getText().strip()
                    print(auction_name)
                except:
                    pass
                """
                try:
                    auction_num=soup.find('div', {'class': 'numAsta'}).getText().strip()
                    auction_num=''.join(re.findall('\d.*',auction_num))
                except:
                    pass
                try:
                    aTag = product.find('div', {'class': 'image-holder-list'})
                except:
                    aTag = None
                    pass
                if aTag:
                    detailPageUrl = aTag.find("a")['href']
                    #print(detailPageUrl + " @@@@@@@@@@@@@")
                    try:
                        lot_origin_url=detailPageUrl
                    except:
                        pass
                    detailPageSoup = get_soup(detailPageUrl, httpHeaders=self.httpHeaders)
                    try:
                        priceRealized = detailPageSoup.find('div', {'class': 'statoLottoBox'}).getText().strip()
                        price_sold = ''.join(re.findall("\d+", priceRealized.strip()))
                        #print("Sold Price = " + price_sold)
                    except:
                        print("Error7: %s"%sys.exc_info()[1].__str__())
                    #print(artwork_size_notes)
                    if artwork_markings=='':
                        dataset=detailPageSoup.find('div',{'id':'dettaglioLotto'}).getText(separator=u'@').strip().replace('@@@', '@').replace('@@', '@').split("@")
                        try:
                            if artwork_materials=='':
                                artwork_materials = getMaterial(dataset)
                                artwork_materials = artwork_materials.replace('"', "").replace("'", "")
                        except:
                            pass
                        try:
                            artwork_markings = getSignature(dataset)
                            artwork_markings = artwork_markings.replace('"', "").replace("'", "").replace(";", " ").replace(",", " ")
                        except:
                            pass

                    try:
                        #images=detailPageSoup.find('div',{'class':'caroufredsel_wrapper_bigDetail'}).findAll('a')
                        images=detailPageSoup.find('div',{'id':'carousel'}).findAll('a')
                        #print(images)
                    except:
                        pass

                    try:
                        artwork_images1 = 'https://www.pananti.com'+images[0]['href']
                        print(artwork_images1)
                        #image1_name = scrapperName + '-' + auction_start_date + '-' + auctionId + '-' + lot_num + '-' + price_estimate_min + '-a' + '.jpg'
                        processedArtistName = artist_name.replace(" ", "_")
                        processedArtistName = unidecode.unidecode(processedArtistName)
                        image1_name = auctionId + "__" + processedArtistName + "__" + str(lot_num) + "_a.jpg"
                        image1_name = image1_name.replace('_', '-')
                    except:
                        pass
                    try:
                        artwork_images2 = 'https://www.pananti.com'+images[1]['href']
                        # print(artwork_images2)
                        #image2_name = scrapperName + '-' + auction_start_date + '-' + auctionId + '-' + lot_num + '-' + price_estimate_min + '-b' + '.jpg'
                        processedArtistName = artist_name.replace(" ", "_")
                        processedArtistName = unidecode.unidecode(processedArtistName)
                        image2_name = auctionId + "__" + processedArtistName + "__" + str(lot_num) + "_b.jpg"
                        image2_name = image2_name.replace('_', '-')
                    except:
                        pass
                    if artwork_images1=='':
                        try:
                            images = detailPageSoup.find('div', {'id': 'lottoImg'}).find('a')
                            print(images),'========================================================='
                        except:
                            pass

                        try:
                            artwork_images1 = 'https://www.pananti.com' + images['href']
                            print(artwork_images1)
                            #image1_name = scrapperName + '-' + auction_start_date + '-' + auctionId + '-' + lot_num + '-' + price_estimate_min + '-a' + '.jpg'
                            processedArtistName = artist_name.replace(" ", "_")
                            processedArtistName = unidecode.unidecode(processedArtistName)
                            image1_name = auctionId + "__" + processedArtistName + "__" + str(lot_num) + "_a.jpg"
                            image1_name = image1_name.replace('_', '-')
                        except:
                            pass

                    try:
                        artwork_description = "<strong><br>Description:</strong><br>" + '  ' + lot_num +''+artist_name+'  ' + artwork_name + '  ' + detailPageSoup.find('div', {'id': 'dettLotDx'}).getText()
                        artwork_description = artwork_description.replace('"', "").replace("'", "").replace(";", " ").replace(",", " ")
                    except:
                        pass
                    try:
                        date = detailPageSoup.find('div', {'class': 'titoloHead'}).getText().strip()
                        print(date)
                        date_data = date.replace(',', '').split(' ')
                        print(date_data)
                        date = date_data[0]
                        months = date_data[1][:3]
                        year = date_data[-1][-2:]
                        auction_start_date = date + '-' + months + '-' + year
                        print(auction_start_date)
                    except:
                        pass
                    # auction_start_date='21-Oct-11'
                    # auction_end_date='22-Oct-11'

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
                    #auction_start_date='6-Feb-21'
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
    pageurl = "http://216.137.189.57:8080/scrapers/finish/?scrapername=Pananti&auctionnumber=%s&auctionurl=%s&scrapertype=2"%(auctionno, urllib.parse.quote(auctionurl))
    pageResponse = None
    try:
        pageResponse = urllib.request.urlopen(pageurl)
    except:
        print ("Error: %s"%sys.exc_info()[1].__str__())  



if __name__ == "__main__":
    auctionId = sys.argv[2].upper()
    auctionUrl = sys.argv[1]
    csvpath = sys.argv[3]
    imagedir = sys.argv[4]
    auctionUrlparts = auctionUrl.split("?")
    auctionUrl = auctionUrlparts[0]
    domainUrl = ''
    scrapperName = "Pananti"
    downloadImages = True
    if sys.argv.__len__() > 2 and sys.argv[2] == "True":
        downloadImages = "True"
    fp = open(csvpath, "w")
    Scrape(auctionUrl, auctionId, csvpath, imagedir, downloadImages, scrapperName,  fp)
    fp.close()
    updatestatus(auctionId, auctionUrl)


# Example: python pananti.py "https://www.pananti.com/uk/auction-0150-1/antiques-authors-of-xix-and-xx-century.asp" 0150 /home/supmit/work/art2/pananti_0150.csv /home/supmit/work/art2/images/pananti/0150 0 0


