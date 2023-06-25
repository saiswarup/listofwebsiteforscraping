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


class AstaguruBot(object):
    
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
        self.httpHeaders = { 'User-Agent' : r'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36',  'Accept' : 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8', 'Accept-Language' : 'en-GB,en-US;q=0.9,en;q=0.8', 'Accept-Encoding' : 'gzip,deflate', 'Accept-Charset' : 'ISO-8859-1,utf-8;q=0.7,*;q=0.7', 'Keep-Alive' : '115', 'Connection' : 'keep-alive', }
        self.httpHeaders['cache-control'] = "max-age=0"
        self.httpHeaders['upgrade-insecure-requests'] = "1"
        self.httpHeaders['sec-fetch-dest'] = "document"
        self.httpHeaders['sec-fetch-mode'] = "navigate"
        self.httpHeaders['sec-fetch-site'] = "same-origin"
        self.httpHeaders['sec-fetch-user'] = "?1"
        self.homeDir = os.getcwd()
        self.requestUrl = auctionurl
        self.auctionurl = auctionurl
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
        dd = datestrcomponents[1]
        dd = dd.replace(",", "")
        mm = '01'
        datestrcomponents[0] = datestrcomponents[0].capitalize()
        if datestrcomponents[0] in mondict.keys():
            mm = mondict[datestrcomponents[0]]
        else:
            try:
                mm = mondict3[datestrcomponents[0]]
            except:
                mm = mondict4[datestrcomponents[0]]
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
        payload = "{\"authkey_web\":\"\",\"authkey_mobile\":\"\",\"userid\":\"\",\"CRMClientID\":\"\",\"AuctionId\":\"%s\"}"%self.saleno
        httpheaders = {}
        for hdr in self.httpHeaders.keys():
            httpheaders[hdr] = self.httpHeaders[hdr]
        httpheaders['Content-Type'] = "application/json"
        httpheaders['Accept'] = "application/json, text/plain, */*"
        httpheaders['Origin'] = "https://www.astaguru.com"
        httpheaders['Referer'] = "https://www.astaguru.com/"
        httpheaders['Content-Length'] = payload.__len__()
        httpheaders['sec-ch-ua'] = "\"Chromium\";v=\"110\", \"Not A(Brand\";v=\"24\", \"Google Chrome\";v=\"110\""
        httpheaders['sec-ch-ua-mobile'] = "?1"
        httpheaders['sec-ch-ua-platform'] = "Android"
        httpheaders['sec-fetch-dest'] = "empty"
        httpheaders['sec-fetch-mode'] = "cors"
        httpheaders['sec-fetch-site'] = "same-site"
        apiurl = "https://api-prod.astaguru.com/WebApiModel/UpcomingLots"
        apirequest = urllib.request.Request(apiurl, data=payload.encode('utf-8'), headers=httpheaders)
        apiresponse = self.opener.open(apirequest)
        self.currentPageContent = apiresponse.read()
        pageContent = self.currentPageContent
        datadict = json.loads(pageContent)
        try:
            lotslist = datadict['result']['lots']
        except:
            lotslist = []
        return lotslist
        

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


    def parseDetailPage(self, lotid, lotno, imagepath, artistname, artworkname, downloadimages):
        baseUrl = "https://astaguru.com"
        detailData = {}
        payload = "{\"authkey_web\":\"\",\"authkey_mobile\":\"\",\"userid\":\"\",\"CRMClientID\":\"\",\"LotId\":\"%s\"}"%lotid
        apiurl = 'https://api-prod.astaguru.com/WebApiModel/GetLotDetails'
        httpheaders = {}
        for hdr in self.httpHeaders.keys():
            httpheaders[hdr] = self.httpHeaders[hdr]
        httpheaders['Content-Type'] = "application/json"
        httpheaders['Accept'] = "application/json, text/plain, */*"
        httpheaders['Origin'] = "https://www.astaguru.com"
        httpheaders['Referer'] = "https://www.astaguru.com/"
        httpheaders['Content-Length'] = payload.__len__()
        httpheaders['sec-ch-ua'] = "\"Chromium\";v=\"110\", \"Not A(Brand\";v=\"24\", \"Google Chrome\";v=\"110\""
        httpheaders['sec-ch-ua-mobile'] = "?1"
        httpheaders['sec-ch-ua-platform'] = "Android"
        httpheaders['sec-fetch-dest'] = "empty"
        httpheaders['sec-fetch-mode'] = "cors"
        httpheaders['sec-fetch-site'] = "same-site"
        httpheaders['pragma'] = "no-cache"
        httpheaders['cache-control'] = "no-cache"
        apirequest = urllib.request.Request(apiurl, data=payload.encode('utf-8'), headers=httpheaders)
        apiresponse = self.opener.open(apirequest)
        self.currentPageContent = apiresponse.read()
        pageContent = self.currentPageContent
        datadict = json.loads(pageContent.decode('utf-8', 'ignore'))
        try:
            images = datadict['result']['lots'][0]['Images']
            if images is not None and type(images) == list:
                for img in images:
                    imgurl = img['BigImage']
                    imagename1 = self.getImagenameFromUrl(imgurl)
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
                    imagepathparts = imgurl.split("/")
                    defimageurl = "/".join(imagepathparts[:-2])
                    encryptedFilename = str(encryptedFilename).replace("b'", "")
                    encryptedFilename = str(encryptedFilename).replace("'", "")
                    detailData['image1_name'] = str(encryptedFilename) + ".jpg"
                    detailData['artwork_images1'] = imgurl
        except:
            pass
        detailData['artwork_provenance'] = ""
        detailData['artwork_literature'] = ""
        detailData['artwork_exhibited'] = ""
        detailData['auction_house_name'] = "ASTA GURU"
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


    def getInfoFromLotsData(self, htmlList, imagepath, downloadimages):
        baseUrl = "https://astaguru.com"
        info = []
        endSpacePattern = re.compile("\s+$", re.DOTALL)
        soldpricePattern = re.compile("([\d\s\.,]+)\s+€")
        beginspacePattern = re.compile("^\s+")
        mediumPattern = re.compile("medium", re.IGNORECASE|re.DOTALL)
        sizePattern = re.compile("size", re.IGNORECASE|re.DOTALL)
        yearPattern = re.compile("year", re.IGNORECASE|re.DOTALL)
        estimatePattern = re.compile("estimate", re.IGNORECASE|re.DOTALL)
        lottitlePattern = re.compile("Lot\s+(\d+)\s+(.*)\s*$", re.DOTALL)
        currencyPattern = re.compile("Rs\.?", re.DOTALL)
        measureunitPattern = re.compile("([a-zA-Z]{2})")
        matcatdict_en = {}
        matcatdict_fr = {}
        with open("docs/fineart_materials.csv", newline='') as mapfile:
        #with open("/root/artwork/deploydirnew/docs/fineart_materials.csv", newline='') as mapfile:
            mapreader = csv.reader(mapfile, delimiter=",", quotechar='"')
            for maprow in mapreader:
                matcatdict_en[maprow[1]] = maprow[3]
                matcatdict_fr[maprow[2]] = maprow[3]
        mapfile.close()
        urlparts = self.auctionurl.split("/")
        urlparts.pop()
        urlparts.pop()
        urlprefix = "/".join(urlparts)
        for htmldiv in htmlList:
            data = {}
            data['auction_num'] = self.saleno
            lotno = htmldiv['LotNumber'].strip()
            data['lot_num'] = lotno
            data['artist_name'] = str(htmldiv['ArtistName']).replace("\n", " ").replace("\r", " ")
            if data['artist_name'] == "" or data['artist_name'] is 'None':
                data['artist_name'] = str(htmldiv['Info']['Title'])
            artistname = data['artist_name']
            data['artwork_name'] = str(htmldiv['Info']['LotTitle']).replace("\n", " ").replace("\r", " ")
            artworkname = htmldiv['Info']['LotTitle']
            data['artwork_size_notes'] = str(htmldiv['Info']['Size']).replace("\n", " ").replace("\r", " ")
            data['artwork_materials'] = str(htmldiv['Info']['Medium']).replace("\n", " ").replace("\r", " ")
            data['artwork_start_year'] = str(htmldiv['Info']['Year']).replace("\n", " ").replace("\r", " ")
            data['price_estimate_min'] = str(htmldiv['EstimateFrom']['INR']).replace("\n", " ").replace("\r", " ")
            data['price_estimate_max'] = str(htmldiv['EstimateTo']['INR']).replace("\n", " ").replace("\r", " ")
            aucdate = str(htmldiv['AuctionDate']).replace("\n", " ").replace("\r", " ")
            if aucdate == "":
                aucdate = htmldiv['AuctionDated']
            datepattern = re.compile("(\w+)\s+(\d+)\s*(\-?.*)(\d{4})", re.DOTALL)
            dps = re.search(datepattern, aucdate)
            if dps:
                data['auction_start_date'] = dps.groups()[0] + " " + dps.groups()[1] + " " + dps.groups()[3]
                data['auction_end_date'] = dps.groups()[0] + " " + dps.groups()[2] + " " + dps.groups()[3]
                data['auction_end_date'] = data['auction_end_date'].replace("-", "").replace(",", "")
                self.auctiondate = data['auction_start_date']
            data['artwork_markings'] = str(htmldiv['LotDetDesc']).replace("\n", " ").replace("\r", " ")
            lotid = htmldiv['LotId']
            data['lot_origin_url'] = urlprefix + "/" + str(htmldiv['LotURL'])
            images = htmldiv['Images']
            imgctr= 1
            if images is not None and type(images) == list:
                for img in images:
                    imgurl = str(img['BigImage']).replace("\n", " ").replace("\r", " ")
                    if imgctr == 1:
                        imagename1 = self.getImagenameFromUrl(imgurl)
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
                        imagepathparts = imgurl.split("/")
                        defimageurl = "/".join(imagepathparts[:-2])
                        encryptedFilename = str(encryptedFilename).replace("b'", "")
                        encryptedFilename = str(encryptedFilename).replace("'", "")
                        data['image1_name'] = str(encryptedFilename) + ".jpg"
                        data['artwork_images1'] = imgurl
                    elif imgctr == 2:
                        pass
                    imgctr += 1
            if htmldiv['LiveStatus']['Status'] == "": # Lot hasn't been sold yet
                data['price_sold'] = ""
            else:
                data['price_sold'] = str(htmldiv['LiveStatus']['CurrentBid']['INR'])
            data['artwork_description'] = "Lot Id: " + str(data['lot_num']) + " Artist: " + str(data['artist_name']) + " Artwork Title: " + str(data['artwork_name']) + " Size: " + str(data['artwork_size_notes']) + " Medium: " + str(data['artwork_materials']) +  " Min Estimate: " + str(data['price_estimate_min']) + " Max Estimate: " + str(data['price_estimate_max']) + " Provenance: '' Literature: '' Exhibitions: ''"
            print(data['lot_num'] + " ## " + data['artist_name'] + " ## " + data['artwork_name'] + " ## " + data['artwork_materials'] + " ## " + data['price_estimate_min'])
            if not lotno:
                continue
            if 'artwork_size_notes' in data.keys():
                data['artwork_size_notes'] = data['artwork_size_notes'].lower()
                sizeparts = data['artwork_size_notes'].split('x')
                data['artwork_measurements_height'] = sizeparts[0]
                if sizeparts.__len__() > 1:
                    mups = re.search(measureunitPattern, sizeparts[1])
                    if mups:
                        data['auction_measureunit'] = mups.groups()[0]
                        sizeparts[1] = measureunitPattern.sub("", sizeparts[1])
                    data['artwork_measurements_width'] = sizeparts[1]
                if sizeparts.__len__() > 2:
                    mups = re.search(measureunitPattern, sizeparts[2])
                    if mups:
                        data['auction_measureunit'] = mups.groups()[0]
                        sizeparts[2] = measureunitPattern.sub("", sizeparts[2])
                    data['artwork_measurements_depth'] = sizeparts[2]
            if 'artwork_materials' in data.keys() and 'artwork_category' not in data.keys():
                materials = data['artwork_materials']
                materialparts = materials.split(" ")
                catfound = 0
                for matpart in materialparts:
                    if matpart in ['in', 'on', 'of', 'the', 'from']:
                        continue
                    try:
                        matPattern = re.compile(matpart, re.IGNORECASE|re.DOTALL)
                        for enkey in matcatdict_en.keys():
                            if re.search(matPattern, enkey):
                                data['artwork_category'] = matcatdict_en[enkey]
                                catfound = 1
                                break
                        for frkey in matcatdict_fr.keys():
                            if re.search(matPattern, frkey):
                                data['artwork_category'] = matcatdict_fr[frkey]
                                catfound = 1
                                break
                        if catfound:
                            break
                    except:
                        pass
            print("Getting '%s'..."%data['lot_origin_url'])
            detailUrl = data['lot_origin_url']
            #detailsPageContent = self.getDetailsPage(detailUrl)
            detailData = self.parseDetailPage(lotid, lotno, imagepath, data['artist_name'], data['artwork_name'], downloadimages)
            for k in detailData.keys():
                if k == 'artwork_images1':
                    if k in data.keys() and (data[k] == "" or data[k] is None):
                        data[k] = detailData[k]
                    else:
                        if k not in data.keys():
                            data[k] = detailData[k]
                        else:
                            pass
                else:
                    data[k] = detailData[k]
            withdrawnPattern = re.compile("withdrawn", re.IGNORECASE|re.DOTALL)
            data['price_kind'] = "unknown"
            if ('price_sold' in data.keys() and re.search(withdrawnPattern, data['price_sold'])) or ('price_estimate_max' in data.keys() and re.search(withdrawnPattern, data['price_estimate_max'])):
                data['price_kind'] = "withdrawn"
            elif 'price_sold' in data.keys() and data['price_sold'] != "":
                data['price_kind'] = "price realized"
            elif 'price_estimate_max' in data.keys() and data['price_estimate_max'] != "":
                data['price_kind'] = "estimate"
            else:
                pass
            #data['auction_start_date'] = self.__class__.formatDate(self.auctiondate)
            data['auction_name'] = self.auctiontitle
            data['auction_location'] = "Mumbai, India"
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
    pageurl = "http://216.137.189.57:8080/scrapers/finish/?scrapername=Astaguru&auctionnumber=%s&auctionurl=%s&scrapertype=2"%(auctionno, urllib.parse.quote(auctionurl))
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
    astaguru = AstaguruBot(auctionurl, auctionnumber)
    fp = open(csvpath, "w")
    fieldnames = ['auction_house_name', 'auction_location', 'auction_num', 'auction_start_date', 'auction_end_date', 'auction_name', 'lot_num', 'sublot_num', 'price_kind', 'price_estimate_min', 'price_estimate_max', 'price_sold', 'artist_name', 'artist_birth', 'artist_death', 'artist_nationality', 'artwork_name', 'artwork_year_identifier', 'artwork_start_year', 'artwork_end_year', 'artwork_materials', 'artwork_category', 'artwork_markings', 'artwork_edition', 'artwork_description', 'artwork_measurements_height', 'artwork_measurements_width', 'artwork_measurements_depth', 'artwork_size_notes', 'auction_measureunit', 'artwork_condition_in', 'artwork_provenance', 'artwork_exhibited', 'artwork_literature', 'artwork_images1', 'artwork_images2', 'artwork_images3', 'artwork_images4', 'artwork_images5', 'image1_name', 'image2_name', 'image3_name', 'image4_name', 'image5_name', 'lot_origin_url']
    fieldsstr = ",".join(fieldnames)
    fp.write(fieldsstr + "\n")
    pagectr = 1
    while True:
        soup = BeautifulSoup(astaguru.currentPageContent, features="html.parser")
        lotsdata = astaguru.getLotsFromPage()
        info = astaguru.getInfoFromLotsData(lotsdata, imagepath, downloadimages)
        lotctr = 0 
        for d in info:
            lotctr += 1
            for f in fieldnames:
                if f in d and d[f] is not None:
                    fp.write('"' + str(d[f]) + '",')
                else:
                    fp.write('"",')
            fp.write("\n")
        pagectr += 1
        nextpageanchors = soup.find_all("a", {'class' : 'page-link'})
        nextpagefoundflag = False
        for anchortag in nextpageanchors:
            if 'aria-label' not in anchortag.attrs.keys() or anchortag['aria-label'] != "Next":
                continue
            else:
                nextpagefoundflag = True
            if not nextpagefoundflag:
                break
            nextpageUrl = anchortag['href']
            astaguru.pageRequest = urllib.request.Request(nextpageUrl, headers=astaguru.httpHeaders)
            try:
                astaguru.pageResponse = astaguru.opener.open(astaguru.pageRequest)
            except:
                print("Couldn't find the page %s"%str(pagectr))
                break
            astaguru.currentPageContent = astaguru.__class__._decodeGzippedContent(astaguru.getPageContent())
        if not nextpagefoundflag:
            break
    fp.close()
    updatestatus(auctionnumber, auctionurl)

# Example: python astaguru.py "https://astaguru.com/Upcoming/UpcomingPreview/Modern-Indian-Art-sep2021" 2021 /home/supmit/work/art2/astaguru_2021.csv /home/supmit/work/art2/images/astaguru/2021 0 0

# supmit

