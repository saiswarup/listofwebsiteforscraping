# -*- coding: utf-8 -*-
import os, sys, re
import urllib, urllib.request
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import unicodedata
import io
import gzip
import time
import simplejson as json
import datetime
import string
import requests
from requests_toolbelt.adapters.source import SourceAddressAdapter
from urllib.parse import urlencode, quote_plus
import html
from cryptography.fernet import Fernet
import csv
import unidecode

partialUrlPattern = re.compile("^/\w+")

def decodeHtmlEntities(content):
    entitiesDict = {'&nbsp;' : ' ', '&quot;' : '"', '&lt;' : '<', '&gt;' : '>', '&amp;' : '&', '&apos;' : "'", '&#160;' : ' ', '&#60;' : '<', '&#62;' : '>', '&#38;' : '&', '&#34;' : '"', '&#39;' : "'"}
    for entity in entitiesDict.keys():
        content = content.replace(entity, entitiesDict[entity])
    return(content)


# Implement signal handler for ctrl+c here.
def setSignal():
    pass

class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def http_error_302(self, req, fp, code, msg, headers):
        infourl = urllib.response.addinfourl(fp, headers, req.get_full_url())
        infourl.status = code
        infourl.code = code
        return infourl

    http_error_300 = http_error_302
    http_error_301 = http_error_302
    http_error_303 = http_error_302
    http_error_307 = http_error_302


def unicodefraction_to_decimal(v):
    fracPattern = re.compile("(\d*)\s*([^\s\.\,;a-zA-Z]+)")
    fps = re.search(fracPattern, v)
    if fps:
        fpsg = fps.groups()
        wholenumber = fpsg[0]
        fraction = fpsg[1]
        decimal = round(unicodedata.numeric(fraction), 3)
        if wholenumber:
            decimalstr = str(decimal).replace("0.", ".")
        else:
            decimalstr = str(decimal)
        value = wholenumber + decimalstr
        return value
    return v


class LamodernBot(object):
    
    htmltagPattern = re.compile("\<\/?[^\<\>]*\/?\>", re.DOTALL)
    pathEndingWithSlashPattern = re.compile(r"\/$")

    htmlEntitiesDict = {'&nbsp;' : ' ', '&#160;' : ' ', '&amp;' : '&', '&#38;' : '&', '&lt;' : '<', '&#60;' : '<', '&gt;' : '>', '&#62;' : '>', '&apos;' : '\'', '&#39;' : '\'', '&quot;' : '"', '&#34;' : '"'}

    def __init__(self, auctionurl, auctionnumber):
        # Create the opener object(s). Might need more than one type if we need to get pages with unwanted redirects.
        self.opener = urllib.request.build_opener(urllib.request.HTTPHandler(), urllib.request.HTTPSHandler()) # This is my normal opener....
        self.no_redirect_opener = urllib.request.build_opener(urllib.request.HTTPHandler(), urllib.request.HTTPSHandler(), NoRedirectHandler()) # ... and this one won't handle redirects.
        #self.debug_opener = urllib.request.build_opener(urllib.request.HTTPHandler(debuglevel=1))
        # Initialize some object properties.
        self.sessionCookies = ""
        self.httpHeaders = { 'User-Agent' : r'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36',  'Accept' : 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8', 'Accept-Language' : 'en-us,en;q=0.5', 'Accept-Encoding' : 'gzip,deflate', 'Accept-Charset' : 'ISO-8859-1,utf-8;q=0.7,*;q=0.7', 'Keep-Alive' : '115', 'Connection' : 'keep-alive', }
        self.httpHeaders['cache-control'] = "max-age=0"
        self.httpHeaders['upgrade-insecure-requests'] = "1"
        self.httpHeaders['sec-fetch-dest'] = "document"
        self.httpHeaders['sec-fetch-mode'] = "navigate"
        self.httpHeaders['sec-fetch-site'] = "same-origin"
        self.httpHeaders['sec-fetch-user'] = "?1"
        self.httpHeaders['Referer'] = auctionurl
        self.homeDir = os.getcwd()
        self.auctionurl = auctionurl
        self.requestUrl = auctionurl
        parsedUrl = urlparse(self.requestUrl)
        self.baseUrl = parsedUrl.scheme + "://" + parsedUrl.netloc + "/"
        #print(self.requestUrl)
        self.pageRequest = urllib.request.Request(self.requestUrl, headers=self.httpHeaders)
        self.pageResponse = None
        self.requestMethod = "GET"
        self.postData = {}
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
            sys.exit()
        self.httpHeaders["Referer"] = self.requestUrl
        self.sessionCookies = self.__class__._getCookieFromResponse(self.pageResponse)
        self.httpHeaders["Cookie"] = self.sessionCookies
        # Initialize the account related variables...
        self.currentPageContent = self.__class__._decodeGzippedContent(self.getPageContent())
        self.currentPageNumber = 1 # Page number of the page that is currently being read.
        self.data = {'auction_house_name': '', 'auction_location' : '', 'auction_num' : '', 'auction_start_date' : '', 'auction_end_date' : '', 'auction_name' : '', 'lot_num' : '', 'sublot_num' : '', 'price_kind' : '', 'price_estimate_min' : '', 'price_estimate_max' : '', 'price_sold' : '', 'artist_name' : '', 'artist_birth' : '', 'artist_death' : '', 'artist_nationality' : '', 'artwork_name' : '', 'artwork_year_identifier' : '', 'artwork_start_year' : '', 'artwork_end_year' : '', 'artwork_materials' : '', 'artwork_category' : '', 'artwork_markings' : '', 'artwork_edition' : '', 'artwork_description' : '', 'artwork_measurements_height' : '', 'artwork_measurements_width' : '', 'artwork_measurements_depth' : '', 'artwork_size_notes' : '', 'auction_measureunit' : '', 'artwork_condition_in' : '', 'artwork_provenance' : '', 'artwork_exhibited' : '', 'artwork_literature' : '', 'artwork_images1' : '', 'artwork_images2' : '', 'artwork_images3' : '', 'artwork_images4' : '', 'artwork_images5' : '', 'image1_name' : '', 'image2_name' : '', 'image3_name' : '', 'image4_name' : '', 'image5_name' : '', 'lot_origin_url' : ''}
        self.saleno = auctionnumber
        self.auctiondate = ""
        self.auctiontitle = ""



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


    def _getCookieFromResponse(cls, lastHttpResponse):
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


    def getPageContent(self):
        return(self.pageResponse.read())

    def formatDate(cls, datestr):
        mondict = {'January' : '01', 'February' : '02', 'March' : '03', 'April' : '04', 'May' : '05', 'June' : '06', 'July' : '07', 'August' : '08', 'September' : '09', 'October' : '10', 'November' : '11', 'December' : '12' }
        mondict3 = {'jan.' : '01', 'fév.' : '02', 'mar.' : '03', 'avr.' : '04', 'mai.' : '05', 'jui.' : '06', 'jul.' : '07', 'aoû.' : '08', 'sep.' : '09', 'oct.' : '10', 'nov.' : '11', 'déc.' : '12' }
        mondict4 = {'Janvier' : '01', 'Février' : '02', 'Mars' : '03', 'Avril' : '04', 'Mai' : '05', 'Juin' : '06', 'Juillet' : '07', 'Août' : '08', 'Septembre' : '09', 'Octobre' : '10', 'Novembre' : '11', 'Décembre' : '12'}
        datestrcomponents = datestr.split(" ")
        if not datestr:
            return ""
        dd = datestrcomponents[0]
        mm = '01'
        datestrcomponents[1] = datestrcomponents[1].capitalize()
        if datestrcomponents[1] in mondict.keys():
            mm = mondict[datestrcomponents[1]]
        else:
            try:
                mm = mondict3[datestrcomponents[1]]
            except:
                mm = mondict4[datestrcomponents[1]]
        yyyy = datestrcomponents[2]
        retdate = mm + "/" + dd + "/" + yyyy
        return retdate

    formatDate = classmethod(formatDate)


    def fractionToDecimalSize(self, sizestring):
        sizestringparts = sizestring.split("x")
        if sizestringparts.__len__() < 1:
            sizestringparts = sizestring.split("by")
        unitPattern = re.compile("(\s*(in)|(cm)\s*$)", re.IGNORECASE)
        ups = re.search(unitPattern, sizestringparts[-1])
        unit = ""
        if ups:
            upsg = ups.groups()
            unit = upsg[0]
        sizestringparts[-1] = unitPattern.sub("", sizestringparts[-1])
        decimalsizeparts = []
        beginspacePattern = re.compile("^\s+")
        endspacePattern = re.compile("\s+$")
        for szpart in sizestringparts:
            szpart = beginspacePattern.sub("", szpart)
            szpart = endspacePattern.sub("", szpart)
            d_szpart = unicodefraction_to_decimal(szpart)
            decimalsizeparts.append(d_szpart)
        decimalsize = " x ".join(decimalsizeparts)
        decimalsize += " " + unit
        return decimalsize


    def getLotsFromPage(self):
        pageContent = self.currentPageContent
        soup = BeautifulSoup(pageContent, features="html.parser")
     
        allanchors = soup.find_all("a", {'class' : 'mosaic-text'})
        titletags = soup.find_all("title")
        print(titletags)
        if titletags.__len__() > 0:
            titlecontents = titletags[0].renderContents().decode('utf-8')
            titlePattern = re.compile("([\w\+\s]+)\,\s+(\d{2}\s+\w+\s+\d{4})")
            tps = re.search(titlePattern, titlecontents)
            if tps:
                tpsg = tps.groups()
                self.auctiontitle = tpsg[0]
                self.auctiondate = tpsg[1]
        lotblocks = allanchors
        #print(lotblocks.__len__())
        return lotblocks
        

    def getDetailsPage(self, detailUrl):
        self.requestUrl = detailUrl
        self.pageRequest = urllib.request.Request(self.requestUrl, headers=self.httpHeaders)
        self.pageResponse = None
        self.postData = {}
        try:
            self.pageResponse = self.opener.open(self.pageRequest)
            headers = self.pageResponse.getheaders()
        except:
            print ("Couldn't fetch page due to limited connectivity. Please check your internet connection and try again. %s"%sys.exc_info()[1].__str__())
        self.currentPageContent = self.__class__._decodeGzippedContent(self.getPageContent())
        return self.currentPageContent


    def encryptFilename(self, filename):
        k = Fernet.generate_key()
        f = Fernet(k)
        encfilename = f.encrypt(filename.encode())
        return encfilename


    def renameImagefile(self, basepath, imagefilename, mappedImagename):
        oldfilename = basepath + "/" + imagefilename
        newfilename = basepath + "/" + mappedImagename
        try:
            os.rename(oldfilename, newfilename)
        except:
            print(oldfilename)


    def getImagenameFromUrl(self, imageUrl):
        urlparts = imageUrl.split("/")
        imagefilepart = urlparts[-1]
        imagefilenameparts = imagefilepart.split("?")
        imagefilename = imagefilenameparts[0]
        return imagefilename


    def parseDetailPage(self, detailsPage, lotno, imagepath, artistname, artworkname, downloadimages):
        baseUrl = "https://auction.lamodern.com"
        detailData = {}
        matcatdict_en = {}
        matcatdict_fr = {}
        #with open("docs/fineart_materials.csv", newline='') as mapfile:
        with open("/Users/saiswarupsahu/freelanceprojectchetan/docs/fineart_materials.csv", newline='') as mapfile:
            mapreader = csv.reader(mapfile, delimiter=",", quotechar='"')
            for maprow in mapreader:
                matcatdict_en[maprow[1]] = maprow[3]
                matcatdict_fr[maprow[2]] = maprow[3]
        mapfile.close()
        soup = BeautifulSoup(detailsPage, features="html.parser")
        descmetatags = soup.find_all("meta", {'name' : 'description'})
        if descmetatags.__len__() > 0:
            metacontents = descmetatags[0]['content']
            bdPattern1 = re.compile("(\d{4})–(\d{4})")
            bdPattern2 = re.compile("b[\.orn]{1,4}\s+(\d{4})", re.IGNORECASE)
            bdps1 = re.search(bdPattern1, metacontents)
            bdps2 = re.search(bdPattern2, metacontents)
            if bdps1:
                birthdate = bdps1.groups()[0]
                deathdate = bdps1.groups()[1]
                detailData['artist_birth'] = birthdate
                detailData['artist_death'] = deathdate
            elif bdps2:
                birthdate = bdps2.groups()[0]
                detailData['artist_birth'] = birthdate
        lotdatacachePattern = re.compile("window\.lot_data_cache\s+=\s+(\{.*\}\}\});")
        lps = re.search(lotdatacachePattern, detailsPage)
        if lps:
            lotdata = lps.groups()[0]
            lotjson = json.loads(lotdata)
            itemdict = lotjson['lot_' + str(lotno)]['item']
            yearPattern = re.compile("(\d{4})")
            #print(itemdict.keys())
            if 'artist_birth' not in detailData.keys():
                if 'year_of_birth' in itemdict.keys():
                    birthdate = itemdict['year_of_birth']
                else:
                    birthdate = ""
                yps1 = re.search(yearPattern, str(birthdate))
                if yps1:
                    detailData['artist_birth'] = yps1.groups()[0]
                if 'year_of_death' in itemdict.keys():
                    deathdate = itemdict['year_of_death']
                else:
                    deathdate = ""
                yps2 = re.search(yearPattern, str(deathdate))
                if yps2:
                    detailData['artist_death'] = yps2.groups()[0]
            if 'year_designed' in itemdict.keys() and itemdict['year_designed'] is not None:
                detailData['artwork_start_year'] = str(itemdict['year_designed'])
            if 'year_produced' in itemdict.keys() and itemdict['year_produced'] is not None:
                detailData['artwork_start_year'] = str(itemdict['year_produced'])
            if 'material' in itemdict.keys():
                detailData['artwork_materials'] = itemdict['material']
            width, depth, height, dia, length = "", "", "", "", ""
            if 'width' in itemdict.keys() and itemdict['width'] is not None:
                width = itemdict['width']
            if 'depth' in itemdict.keys() and itemdict['depth'] is not None:
                depth = itemdict['depth']
            if 'height' in itemdict.keys() and itemdict['height'] is not None:
                height = itemdict['height']
            if 'diameter' in itemdict.keys() and itemdict['diameter'] is not None:
                dia = itemdict['diameter']
            if 'length' in itemdict.keys() and itemdict['length'] is not None:
                length = itemdict['length']
            if width and height:
                detailData['artwork_measurements_height'] = str(height)
                detailData['artwork_measurements_width'] = str(width)
                detailData['artwork_size_notes'] = str(height) + " x " + str(width)
            if width and height and depth:
                detailData['artwork_measurements_height'] = str(height)
                detailData['artwork_measurements_width'] = str(width)
                detailData['artwork_measurements_depth'] = str(depth)
                detailData['artwork_size_notes'] = str(height) + " x " + str(width) + " x " + str(depth)
            if dia:
                detailData['artwork_measurements_height'] = str(dia)
                detailData['artwork_size_notes'] = "Dia: " + str(dia)
            if length:
                detailData['artwork_measurements_height'] = str(length)
                detailData['artwork_size_notes'] = "Len: " + str(length)
            if 'sale_price' in itemdict.keys():
                detailData['price_sold'] = itemdict['sale_price']
                #print(detailData['price_sold'])
            if 'result_amount' in itemdict.keys() and ('price_sold' not in detailData.keys() or detailData['price_sold'] == "" or detailData['price_sold'] is None or detailData['price_sold'] == 0):
                detailData['price_sold'] = str(itemdict['result_amount']) + " USD"
                #print(detailData['price_sold'])
            if 'result_premium_amount' in itemdict.keys() and ('price_sold' not in detailData.keys() or detailData['price_sold'] == "" or detailData['price_sold'] is None):
                detailData['price_sold'] = str(itemdict['result_premium_amount']) + " USD"
                #print(detailData['price_sold'])
            if 'provenance' in itemdict.keys():
                detailData['artwork_provenance'] = itemdict['provenance']
            if 'literature' in itemdict.keys():
                detailData['artwork_literature'] = itemdict['literature']
            if 'exhibited' in itemdict.keys():
                detailData['artwork_exhibited'] = itemdict['exhibited']
            if 'specifications' in itemdict.keys():
                specs = str(itemdict['specifications'])
                specsparts = specs.split(".")
                for spec in specsparts:
                    if 'sign' in spec:
                        detailData['artwork_markings'] = spec
                    if 'edition' in spec:
                        detailData['artwork_edition'] = spec
            if 'item_condition' in itemdict.keys():
                detailData['artwork_condition_in'] = itemdict['item_condition']
            medialist = lotjson['lot_' + str(lotno)]['item']['combined_media_list']
            if medialist.__len__() > 0:
                defaultimageurl = ""
                if 'data-zoom-src' in medialist[0].keys() and medialist[0]['data-zoom-src'] is not None:
                    defaultimageurl = medialist[0]['data-zoom-src']
                else:
                    defaultimageurl = medialist[0]['src']
                defaultimageurl = defaultimageurl.replace("\\/", "/")
                imagename1 = self.getImagenameFromUrl(defaultimageurl)
                imagename1 = str(imagename1)
                imagename1 = imagename1.replace("b'", "").replace("'", "")
                auctiontitle = self.auctiontitle.replace(" ", "_")
                processedAuctionTitle = auctiontitle.replace(" ", "_")
                processedArtistName = artistname.replace(" ", "_")
                processedArtistName = unidecode.unidecode(processedArtistName)
                processedArtworkName = artworkname.replace(" ", "_")
                sublot_number = ""
                #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + self.saleno + "__" + lotno + "__" + sublot_number
                newname1 = self.saleno + "__" + processedArtistName + "__" + lotno + "_a"
                #encryptedFilename = self.encryptFilename(newname1)
                encryptedFilename = newname1
                imagepathparts = defaultimageurl.split("/")
                defimageurl = "/".join(imagepathparts[:-2])
                encryptedFilename = str(encryptedFilename).replace("b'", "")
                encryptedFilename = str(encryptedFilename).replace("'", "")
                detailData['image1_name'] = str(encryptedFilename) + ".jpg"
                detailData['artwork_images1'] = defaultimageurl
            additionalimages = []
            for media in medialist[1:]:
                altimageurl = ""
                if 'data-zoom-src' in media.keys() and media['data-zoom-src'] is not None:
                    altimageurl = media['data-zoom-src']
                else:
                    altimageurl = media['src']
                altimageurl = altimageurl.replace("\\/", "/")
                additionalimages.append(altimageurl)
            imgctr = 2
            if additionalimages.__len__() > 0:
                altimage2 = additionalimages[0]
                altimage2parts = altimage2.split("/")
                altimageurl = "/".join(altimage2parts[:-2])
                processedArtistName = artistname.replace(" ", "_")
                processedArtistName = unidecode.unidecode(processedArtistName)
                processedArtworkName = artworkname.replace(" ", "_")
                sublot_number = ""
                #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + self.saleno + "__" + lotno + "__" + sublot_number
                newname1 = self.saleno + "__" + processedArtistName + "__" + lotno + "_b"
                #encryptedFilename = self.encryptFilename(newname1)
                encryptedFilename = newname1
                detailData['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
                detailData['artwork_images' + str(imgctr)] = altimage2
                imgctr += 1
            if additionalimages.__len__() > 1:
                altimage2 = additionalimages[1]
                altimage2parts = altimage2.split("/")
                altimageurl = "/".join(altimage2parts[:-2])
                processedArtistName = artistname.replace(" ", "_")
                processedArtistName = unidecode.unidecode(processedArtistName)
                processedArtworkName = artworkname.replace(" ", "_")
                sublot_number = ""
                #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + self.saleno + "__" + lotno + "__" + sublot_number
                newname1 = self.saleno + "__" + processedArtistName + "__" + lotno + "_c"
                #encryptedFilename = self.encryptFilename(newname1)
                encryptedFilename = newname1
                detailData['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
                detailData['artwork_images' + str(imgctr)] = altimage2
                imgctr += 1
            if additionalimages.__len__() > 2:
                altimage2 = additionalimages[2]
                altimage2parts = altimage2.split("/")
                altimageurl = "/".join(altimage2parts[:-2])
                processedArtistName = artistname.replace(" ", "_")
                processedArtistName = unidecode.unidecode(processedArtistName)
                processedArtworkName = artworkname.replace(" ", "_")
                sublot_number = ""
                #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + self.saleno + "__" + lotno + "__" + sublot_number
                newname1 = self.saleno + "__" + processedArtistName + "__" + lotno + "_d"
                #encryptedFilename = self.encryptFilename(newname1)
                encryptedFilename = newname1
                detailData['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
                detailData['artwork_images' + str(imgctr)] = altimage2
                imgctr += 1
            if additionalimages.__len__() > 3:
                altimage2 = additionalimages[3]
                altimage2parts = altimage2.split("/")
                altimageurl = "/".join(altimage2parts[:-2])
                processedArtistName = artistname.replace(" ", "_")
                processedArtistName = unidecode.unidecode(processedArtistName)
                processedArtworkName = artworkname.replace(" ", "_")
                sublot_number = ""
                #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + self.saleno + "__" + lotno + "__" + sublot_number
                newname1 = self.saleno + "__" + processedArtistName + "__" + lotno + "_e"
                #encryptedFilename = self.encryptFilename(newname1)
                encryptedFilename = newname1
                detailData['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
                detailData['artwork_images' + str(imgctr)] = altimage2
        if 'artwork_materials' in detailData.keys() and 'artwork_category' not in detailData.keys():
            materials = detailData['artwork_materials']
            materialparts = materials.split(" ")
            catfound = 0
            for matpart in materialparts:
                if matpart in ['in', 'on', 'of', 'the', 'from']:
                    continue
                try:
                    matPattern = re.compile(matpart, re.IGNORECASE|re.DOTALL)
                    for enkey in matcatdict_en.keys():
                        if re.search(matPattern, enkey):
                            detailData['artwork_category'] = matcatdict_en[enkey]
                            catfound = 1
                            break
                    for frkey in matcatdict_fr.keys():
                        if re.search(matPattern, frkey):
                            detailData['artwork_category'] = matcatdict_fr[frkey]
                            catfound = 1
                            break
                    if catfound:
                        break
                except:
                    pass
        if 'artwork_size_notes' not in detailData.keys():
            detailData['artwork_size_notes'] = ""
        if 'artwork_materials' not in detailData.keys():
            detailData['artwork_materials'] = ""
        if 'artwork_provenance' not in detailData.keys():
            detailData['artwork_provenance'] = ""
        if 'artwork_literature' not in detailData.keys():
            detailData['artwork_literature'] = ""
        if 'artwork_exhibited' not in detailData.keys():
            detailData['artwork_exhibited'] = ""
        detailData['artwork_description'] = str(artworkname) + " " + str(artistname) + " " + str(detailData['artwork_materials']) + " " + str(detailData['artwork_size_notes']) + " Provenance: " + str(detailData['artwork_provenance']) + " Literature: " + str(detailData['artwork_literature']) + " Exhibited: " + str(detailData['artwork_exhibited'])
        detailData['artwork_description'] = "<strong><br>Description<br></strong>" + detailData['artwork_description']
        detailData['artwork_description'] = detailData['artwork_description'].replace('"', "'")
        detailData['auction_house_name'] = "LOS ANGELES MODERN"
        return detailData


    def getImage(self, imageUrl, imagepath, downloadimages):
        imageUrlParts = imageUrl.split("/")
        imagefilename = imageUrlParts[-2] + "_" + imageUrlParts[-1]
        imagedir = imageUrlParts[-2]
        if downloadimages == "1":
            pageRequest = urllib.request.Request(imageUrl, headers=self.httpHeaders)
            pageResponse = None
            try:
                pageResponse = self.opener.open(pageRequest)
            except:
                print ("Error: %s"%sys.exc_info()[1].__str__())
            try:
                imageContent = pageResponse.read()
                ifp = open(imagepath + os.path.sep + imagefilename, "wb")
                ifp.write(imageContent)
                ifp.close()
            except:
                print("Error: %s"%sys.exc_info()[1].__str__())
        return imagefilename


    def getInfoFromLotsData(self, lotslist, imagepath, downloadimages):
        baseUrl = "https://www.lamodern.com"
        info = []
        endSpacePattern = re.compile("\s+$", re.DOTALL)
        soldpricePattern = re.compile("([\d\s\.,]+)\s+€")
        beginspacePattern = re.compile("^\s+")
        yearPattern = re.compile("\d{4}")
        for lotanchor in lotslist:
            data = {}
            data['auction_num'] = self.saleno
            data['artist_name'] = ""
            data['artwork_name'] = ""
            lotnotags = lotanchor.find_all("span", {'class' : 'lot_no'})
            if lotnotags.__len__() > 0:
                lotno = lotnotags[0].renderContents().decode('utf-8')
                lotno = lotno.replace("\n", "").replace("\r", "")
                data['lot_num'] = lotno
            else:
                continue
            artistnametags = lotanchor.find_all("span", {'class' : 'name'})
            if artistnametags.__len__() > 0:
                artistname = artistnametags[0].renderContents().decode('utf-8')
                artistname = artistname.replace("\n", "").replace("\r", "")
                data['artist_name'] = artistname
            titledivtags = lotanchor.find_all("div", {'class' : 'title'})
            if titledivtags.__len__() > 0:
                title = titledivtags[0].renderContents().decode('utf-8')
                title = title.replace("\n", "").replace("\r", "")
                title = self.__class__.htmltagPattern.sub("", title)
                data['artwork_name'] = title
            detailUrl = baseUrl + lotanchor['href']
            data['lot_origin_url'] = detailUrl
            estimatedivtags = lotanchor.find_all("div", {'class' : 'estimate'})
            if estimatedivtags.__len__() > 0:
                estimate = estimatedivtags[0].renderContents().decode('utf-8')
                estimate = estimate.replace("\n", "").replace("\r", "")
                estimate = self.__class__.htmltagPattern.sub("", estimate)
                estimate = estimate.replace("$", "")
                estimate = estimate.replace("–", " - ")
                #estimate = estimate + " USD"
                estimateparts = estimate.split(" - ")
                data['price_estimate_min'] = estimateparts[0]
                if estimateparts.__len__() > 1:
                    data['price_estimate_max'] = estimateparts[1]
            """
            try:
                print(data['lot_num'] + " ## " + data['artist_name'] + " ## " + data['artwork_name'] + " ## " + data['price_estimate_min'])
            except:
                print(data['lot_num'])
            """
            print("Getting '%s'..."%data['lot_origin_url'])
            self.httpHeaders['Referer'] = self.auctionurl
            detailsPageContent = self.getDetailsPage(detailUrl)
            if not lotno:
                continue
            detailData = self.parseDetailPage(detailsPageContent, lotno, imagepath, data['artist_name'], data['artwork_name'], downloadimages)
            for k in detailData.keys():
                data[k] = detailData[k]
            withdrawnPattern = re.compile("withdrawn", re.IGNORECASE|re.DOTALL)
            data['price_kind'] = "unknown"
            if ('price_sold' in data.keys() and re.search(withdrawnPattern, str(data['price_sold']))) or ('price_estimate_max' in data.keys() and re.search(withdrawnPattern, str(data['price_estimate_max']))):
                data['price_kind'] = "withdrawn"
            elif 'price_sold' in data.keys() and data['price_sold'] != "" and data['price_sold'] != "0 USD":
                data['price_kind'] = "price realized"
            elif 'price_estimate_max' in data.keys() and data['price_estimate_max'] != "":
                data['price_kind'] = "estimate"
            else:
                pass
            data['auction_start_date'] = self.auctiondate.replace("\n", " ").replace("\r\n", " ")
            data['auction_start_date'] = self.__class__.formatDate(data['auction_start_date'])
            data['auction_name'] = self.auctiontitle
            data['auction_location'] = "Van Nuys, CA"
            info.append(data)
        return info

"""
[
'auction_house_name', 'auction_location', 'auction_num', 'auction_start_date', 'auction_end_date', 'auction_name', 'lot_num', 'sublot_num', 'price_kind', 'price_estimate_min', 'price_estimate_max', 'price_sold', 'artist_name', 'artist_birth', 'artist_death', 'artist_nationality', 'artwork_name', 'artwork_year_identifier', 'artwork_start_year', 'artwork_end_year', 'artwork_materials', 'artwork_category', 'artwork_markings', 'artwork_edition', 'artwork_description', 'artwork_measurements_height', 'artwork_measurements_width', 'artwork_measurements_depth', 'artwork_size_notes', 'auction_measureunit', 'artwork_condition_in', 'artwork_provenance', 'artwork_exhibited', 'artwork_literature', 'artwork_images1', 'artwork_images2', 'artwork_images3', 'artwork_images4', 'artwork_images5', 'image1_name', 'image2_name', 'image3_name', 'image4_name', 'image5_name', 'lot_origin_url'
]
 """
 
# That's it.... 

def updatestatus(auctionno, auctionurl):
    auctionurl = auctionurl.replace("%3A", ":")
    auctionurl = auctionurl.replace("%2F", "/")
    pageurl = "http://216.137.189.57:8080/scrapers/finish/?scrapername=Losangelesmodern&auctionnumber=%s&auctionurl=%s&scrapertype=2"%(auctionno, urllib.parse.quote(auctionurl))
    pageResponse = None
    try:
        pageResponse = urllib.request.urlopen(pageurl)
    except:
        print ("Error: %s"%sys.exc_info()[1].__str__())  




if __name__ == "__main__":
    if sys.argv.__len__() < 5:
        print("Insufficient parameters")
        
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
    lamodern = LamodernBot(auctionurl, auctionnumber)
    fp = open(csvpath, "w")
    fieldnames = ['auction_house_name', 'auction_location', 'auction_num', 'auction_start_date', 'auction_end_date', 'auction_name', 'lot_num', 'sublot_num', 'price_kind', 'price_estimate_min', 'price_estimate_max', 'price_sold', 'artist_name', 'artist_birth', 'artist_death', 'artist_nationality', 'artwork_name', 'artwork_year_identifier', 'artwork_start_year', 'artwork_end_year', 'artwork_materials', 'artwork_category', 'artwork_markings', 'artwork_edition', 'artwork_description', 'artwork_measurements_height', 'artwork_measurements_width', 'artwork_measurements_depth', 'artwork_size_notes', 'auction_measureunit', 'artwork_condition_in', 'artwork_provenance', 'artwork_exhibited', 'artwork_literature', 'artwork_images1', 'artwork_images2', 'artwork_images3', 'artwork_images4', 'artwork_images5', 'image1_name', 'image2_name', 'image3_name', 'image4_name', 'image5_name', 'lot_origin_url']
    fieldsstr = ",".join(fieldnames)
    fp.write(fieldsstr + "\n")
    lotsdata = lamodern.getLotsFromPage()
    print(lotsdata)
    info = lamodern.getInfoFromLotsData(lotsdata, imagepath, downloadimages)
    lotctr = 0 
    for d in info:
        lotctr += 1
        for f in fieldnames:
            if f in d and d[f] is not None:
                fp.write('"' + str(d[f]) + '",')
            else:
                fp.write('"",')
        fp.write("\n")
    fp.close()
    updatestatus(auctionnumber, auctionurl)

# Example: python lamodern.py https://www.lamodern.com/auctions/2018/06/modern-art-design   201802  /Users/saiswarupsahu/freelanceprojectchetan/iamodern_201802.csv  /Users/saiswarupsahu/freelanceprojectchetan/ 0 0

# supmit

