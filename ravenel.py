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


class RavenelBot(object):
    
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
        self.homeDir = os.getcwd()
        auctionurlparts = auctionurl.split("/")
        auctioncode = auctionurlparts[-1]
        self.requestUrl = "https://ravenel.com/rest/auc/lots/" + auctioncode + "?fuzzyKeyword=&artistName=&orderBy=auctionShowDateASC&auctionYear=&pageIndex=0&pageSize=20&language=en"
        self.httpHeaders['referer'] = auctionurl
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
        jsondata = json.loads(pageContent)
        lotblocks = jsondata['data']
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


    def getInfoFromLotsData(self, datalist, imagepath, downloadimages):
        baseUrl = "https://ravenel.com"
        info = []
        endSpacePattern = re.compile("\s+$", re.DOTALL)
        soldpricePattern = re.compile("([\d\s\.,]+)\s+€")
        beginspacePattern = re.compile("^\s+")
        signedPattern = re.compile("Signed", re.IGNORECASE)
        provenancePattern = re.compile("Provenance", re.IGNORECASE)
        exhibitionPattern = re.compile("Exhibited", re.IGNORECASE)
        measureunitPattern = re.compile("([a-zA-Z]{2})")
        matcatdict_en = {}
        matcatdict_fr = {}
        #with open("docs/fineart_materials.csv", newline='') as mapfile:
        with open("/Users/saiswarupsahu/freelanceprojectchetan/docs/fineart_materials.csv", newline='') as mapfile:
            mapreader = csv.reader(mapfile, delimiter=",", quotechar='"')
            for maprow in mapreader:
                matcatdict_en[maprow[1]] = maprow[3]
                matcatdict_fr[maprow[2]] = maprow[3]
        mapfile.close()
        for datadict in datalist:
            data = {}
            data['auction_num'] = self.saleno
            lotno = ""
            data['artist_name'] = ""
            data['artist_birth'] = ""
            data['artist_death'] = ""
            data['artwork_name'] = ""
            data['artwork_exhibited'] = ""
            data['artwork_provenance'] = ""
            priceslist = datadict['estimatePrice']
            for pricedata in priceslist:
                if pricedata['language'] == "zh-TW":
                    estimate = pricedata['val']
                    estimateparts = estimate.split("-")
                    data['price_estimate_min'] = estimateparts[0]
                    if estimateparts.__len__() > 1:
                        data['price_estimate_max'] = estimateparts[1]
                else:
                    continue
            data['artwork_name'] = datadict['name']
            if 'artist' in datadict.keys():
                data['artist_name'] = datadict['artist']['name']
                try:
                    data['artist_birth'] = datadict['artist']['yearOfBirth']
                    data['artist_death'] = datadict['artist']['yearOfDeath']
                except:
                    data['artist_birth'] = ""
                    data['artist_death'] = ""
            elif 'artistList' in datadict.keys():
                artistlist = datadict['artistList']
                if 'name' in artistlist[0].keys():
                    data['artist_name'] = artistlist[0]['name']
                if 'yearOfBirth' in artistlist[0].keys():
                    data['artist_birth'] = artistlist[0]['yearOfBirth']
                if 'yearOfDeath' in artistlist[0].keys():
                    data['artist_death'] = artistlist[0]['yearOfDeath']
            profileslist = datadict['profile']
            data['artwork_size_notes'] = ""
            for profile in profileslist:
                if profile['profileName'] == "Signature":
                    signature = profile['val']
                    signatureparts = signature.split("<br /><br />")
                    for signpart in signatureparts:
                        sps = re.search(signedPattern, signpart)
                        pps = re.search(provenancePattern, signpart)
                        eps = re.search(exhibitionPattern, signpart)
                        signpart = self.__class__.htmltagPattern.sub("", signpart)
                        if sps:
                            data['artwork_markings'] = signpart
                            data['artwork_markings'] = data['artwork_markings'].replace("\n", " ").replace("\r", "")
                        elif pps:
                            data['artwork_provenance'] = signpart
                            data['artwork_provenance'] = data['artwork_provenance'].replace("\n", " ").replace("\r", "")
                        elif eps:
                            data['artwork_exhibited'] = signpart
                            data['artwork_exhibited'] = data['artwork_exhibited'].replace("\n", " ").replace("\r", "")
                elif profile['profileName'] == "Material":
                    data['artwork_materials'] = profile['val']
                    data['artwork_materials'] = data['artwork_materials'].replace("\n", " ").replace("\r", "")
                elif profile['profileName'] == "Dimension":
                    data['artwork_size_notes'] = profile['val']
                    data['artwork_size_notes'] = data['artwork_size_notes'].replace("\n", " ").replace("\r", "")
                elif profile['profileName'] == "Year":
                    data['artwork_start_year'] = profile['val']
                elif profile['profileName'] == "Guarantee":
                    data['LETTEROFAUTHENTICITY'] = profile['val']
                    data['LETTEROFAUTHENTICITY'] = data['LETTEROFAUTHENTICITY'].replace("\n", " ").replace("\r", "")
            data['lot_num'] = datadict['sn']
            lotno = data['lot_num']
            print(lotno)
            uid = datadict['uid']
            data['lot_origin_url'] = "https://ravenel.com/cata/lotsIn/" + uid
            detailUrl = data['lot_origin_url']
            self.auctiontitle = datadict['lastAuction']
            defaultimageurl = "https://ravenel.com" + datadict['originImgpUrl'][0]
            """
            imagepart = defaultimageurl.split("/")[-1]
            imagefilename = self.getImage(defaultimageurl, imagepath, downloadimages)
            baseImagePath = imagepath
            imszb = os.path.getsize(imagepath + "/" + imagefilename)
            if imszb < 20000: # Any image < 20KB should not be tolerated.
                detailsPageContent = self.getDetailsPage(detailUrl)
                detailsoup = BeautifulSoup(detailsPageContent, features="html.parser")
                carouseldivtags = detailsoup.find_all("div", {'id' : 'myCarousel'})
                if carouseldivtags.__len__() > 0:
                    imgtag = carouseldivtags[0].findNext("img")
                    defaultimageurl = "https://ravenel.com" + imgtag['data-to-link']
                #print(defaultimageurl)
                imagefilename = self.getImage(defaultimageurl, imagepath, downloadimages)
            """
            imagename1 = self.getImagenameFromUrl(defaultimageurl)
            imagename1 = str(imagename1)
            imagename1 = imagename1.replace("b'", "").replace("'", "")
            auctiontitle = self.auctiontitle.replace(" ", "_")
            processedAuctionTitle = auctiontitle.replace(" ", "_")
            processedArtistName = data['artist_name'].replace(" ", "_")
            processedArtistName = unidecode.unidecode(processedArtistName)
            processedArtworkName = data['artwork_name'].replace(" ", "_")
            sublot_number = ""
            #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + self.saleno + "__" + lotno + "__" + sublot_number
            newname1 = self.saleno + "__" + processedArtistName + "__" + str(lotno) + "_a"
            #encryptedFilename = self.encryptFilename(newname1)
            encryptedFilename = newname1
            imagepathparts = defaultimageurl.split("/")
            defimageurl = "/".join(imagepathparts[:-2])
            encryptedFilename = str(encryptedFilename).replace("b'", "")
            encryptedFilename = str(encryptedFilename).replace("'", "")
            data['image1_name'] = str(encryptedFilename) + ".jpg"
            data['artwork_images1'] = defaultimageurl
            soldpriceslist = datadict['finalCurrencyValue']
            for soldpricedict in soldpriceslist:
                if soldpricedict['language'] == "zh-TW" and soldpricedict['displayValue'] != "":
                    soldprice = soldpricedict['displayValue'] + " " + soldpricedict['displayName']
                    data['price_sold'] = soldprice
            sizeparts = data['artwork_size_notes'].split("x")
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
            #print(data['lot_num'] + " ## " + data['artist_name'] + " ## " + data['BIRTHDATE'] + " ## " + data['DEATHDATE'] + " ## " + data['SIZE'])
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
            if 'price_sold' not in data.keys() or data['price_sold'] == "":
                data['price_sold'] = ""
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
            try:
                data['artwork_description'] = data['artwork_name'] + " " + data['artist_name'] + " " + data['artwork_materials'] + " " + data['artwork_size_notes'] + " Provenance: " + data['artwork_provenance'] + " Exhibited: " + data['artwork_exhibited'] 
                data['artwork_description'] = "<strong><br>Description<br></strong>" + detailData['artwork_description']
                data['artwork_description'] = data['artwork_description'].replace('"', "'")
            except:
                data['artwork_description'] = data['artwork_name'] + " " + data['artist_name']
                data['artwork_description'] = "<strong><br>Description<br></strong>" + data['artwork_description']
            data['auction_start_date'] = self.__class__.formatDate(self.auctiondate)
            data['auction_start_date'] = data['auction_start_date'].replace("\n", " ").replace("\r\n", " ")
            data['auction_name'] = self.auctiontitle
            data['auction_house_name'] = "Ravenel"
            data['auction_location'] = "Taipei"
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
    pageurl = "http://216.137.189.57:8080/scrapers/finish/?scrapername=Ravenel&auctionnumber=%s&auctionurl=%s&scrapertype=2"%(auctionno, urllib.parse.quote(auctionurl))
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
    ravenel = RavenelBot(auctionurl, auctionnumber)
    fp = open(csvpath, "w")
    fieldnames = ['auction_house_name', 'auction_location', 'auction_num', 'auction_start_date', 'auction_end_date', 'auction_name', 'lot_num', 'sublot_num', 'price_kind', 'price_estimate_min', 'price_estimate_max', 'price_sold', 'artist_name', 'artist_birth', 'artist_death', 'artist_nationality', 'artwork_name', 'artwork_year_identifier', 'artwork_start_year', 'artwork_end_year', 'artwork_materials', 'artwork_category', 'artwork_markings', 'artwork_edition', 'artwork_description', 'artwork_measurements_height', 'artwork_measurements_width', 'artwork_measurements_depth', 'artwork_size_notes', 'auction_measureunit', 'artwork_condition_in', 'artwork_provenance', 'artwork_exhibited', 'artwork_literature', 'artwork_images1', 'artwork_images2', 'artwork_images3', 'artwork_images4', 'artwork_images5', 'image1_name', 'image2_name', 'image3_name', 'image4_name', 'image5_name', 'lot_origin_url']
    fieldsstr = ",".join(fieldnames)
    fp.write(fieldsstr + "\n")
    auctionurlparts = auctionurl.split("/")
    auctioncode = auctionurlparts[-1]
    pagectr = 0
    while True:
        lotsdata = ravenel.getLotsFromPage()
        if lotsdata.__len__() == 0:
            break
        info = ravenel.getInfoFromLotsData(lotsdata, imagepath, downloadimages)
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
        nextpageUrl = "https://ravenel.com/rest/auc/lots/%s?fuzzyKeyword=&artistName=&orderBy=auctionShowDateASC&auctionYear=&pageIndex=%s&pageSize=20&language=en"%(auctioncode, str(pagectr))
        print(nextpageUrl)
        ravenel.pageRequest = urllib.request.Request(nextpageUrl, headers=ravenel.httpHeaders)
        try:
            ravenel.pageResponse = ravenel.opener.open(ravenel.pageRequest)
        except:
            print("Couldn't find the page %s"%str(pagectr))
            break
        ravenel.currentPageContent = ravenel.__class__._decodeGzippedContent(ravenel.getPageContent())
    fp.close()
    updatestatus(auctionnumber, auctionurl)

# Example: python ravenel.py  https://ravenel.com/au/calendar/auction/fe153b46-e4a7-4d9b-a56c-6336f78c5f9c  10   /Users/saiswarupsahu/freelanceprojectchetan/ravenel_10.csv /Users/saiswarupsahu/freelanceprojectchetan/ 0 0

# Example: python ravenel.py https://ravenel.com/en/au/calendar/auction/40b15a4c-6138-4855-9ebc-f348ef9459fa f348ef9459fa /Users/saiswarupsahu/freelanceprojectchetan/ravenel_9.csv /Users/saiswarupsahu/freelanceprojectchetan/ 0 0


# supmit

