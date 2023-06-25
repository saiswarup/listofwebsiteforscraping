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


class CambiasteBot(object):
    
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
        self.auctionlocation = ""


    def _decodeGzippedContent(cls, encoded_content):
        response_stream = io.BytesIO(encoded_content)
        decoded_content = ""
        try:
            gzipper = gzip.GzipFile(fileobj=response_stream)
            decoded_content = gzipper.read()
        except: # Maybe this isn't gzipped content after all....
            decoded_content = encoded_content
        decoded_content = decoded_content.decode('utf-8', 'ignore')
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
        mondict = {'Janvier' : 'Jan', 'Février' : 'Feb', 'Mars' : 'Mar', 'Avril' : 'Apr', 'Mai' : 'May', 'Juin' : 'Jun', 'Juillet' : 'Jul', 'Août' : 'Aug', 'Septembre' : 'Sep', 'Octobre' : 'Oct', 'Novembre' : 'Nov', 'Décembre' : 'Dec'}
        datestrcomponents = datestr.split("/")
        if not datestr:
            return ""
        if datestrcomponents.__len__() < 3:
            return ""
        dd = datestrcomponents[0]
        mon = datestrcomponents[1].capitalize()
        year = datestrcomponents[2]
        monstr = mon
        if mon in mondict.keys():
            monstr = mondict[mon]
        retdate = dd + "-" + monstr + "-" + year
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
        titlePattern = re.compile("itemListTitle")
        dataPattern = re.compile("itemListData")
        alldivtitletags = soup.find_all("div", {'class' : titlePattern})
        locPattern = re.compile("\w{3}\s+\d{1,2}\s+\w+\s+\d{4}\s+([\w]+)", re.DOTALL)
        endspacePattern = re.compile("\s+$", re.DOTALL)
        if alldivtitletags.__len__() > 0:
            title = alldivtitletags[0].renderContents().decode('utf-8')
            title = self.__class__.htmltagPattern.sub("", title)
            title = title.replace("\n", "").replace("\r", "")
            beginspacePattern = re.compile("^\s+")
            endspacePattern = re.compile("\s+$")
            title = beginspacePattern.sub("", title)
            title = endspacePattern.sub("", title)
            self.auctiontitle = title
        alldatedivtags = soup.find_all("div", {'class' : 'tornata prima'})
        datePattern = re.compile("(\d{1,2}\/\d{1,2}\/\d{4})")
        if alldatedivtags.__len__() > 0:
            datecontent = alldatedivtags[0].renderContents().decode('utf-8')
            dps = re.search(datePattern, datecontent)
            if dps:
                self.auctiondate = dps.groups()[0]
                self.auctiondate = self.auctiondate.replace("\n", "").replace("\r", "")
        alllocationdivtags = soup.find_all("div", {'class' : dataPattern})
        if alllocationdivtags.__len__() > 0:
            locationcontent = alllocationdivtags[0].renderContents().decode('utf-8')
            locationcontent = locationcontent.replace("\n", "").replace("\r", "")
            locationcontent = self.__class__.htmltagPattern.sub("", locationcontent)
            lps = re.search(locPattern, locationcontent)
            if lps:
                self.auctionlocation = lps.groups()[0]
        lotblocks = soup.find_all("div", {'class' : 'lotItemList'})
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

    def renameImageFile(self, basepath, imagefilename, mappedImagename):
        oldfilename = basepath + "/" + imagefilename
        newfilename = basepath + "/" + mappedImagename
        try:
            os.rename(oldfilename, newfilename)
        except:
            pass


    def getImagenameFromUrl(self, imageUrl):
        urlparts = imageUrl.split("/")
        imagefilepart = urlparts[-1]
        imagefilenameparts = imagefilepart.split("?")
        imagefilename = imagefilenameparts[0]
        return imagefilename


    def parseDetailPage(self, detailsPage, artistname, artwork_name, auction_number, lot_number, imagepath, downloadimages):
        baseUrl = "https://www.cambiaste.com"
        detailData = {}
        brPattern = re.compile("<br\s*\/?>")
        beginspacePattern = re.compile("^\s+")
        endspacePattern = re.compile("\s+$")
        literaturePattern = re.compile("Bibliografia", re.IGNORECASE|re.DOTALL)
        provenancePattern = re.compile("Provenienza", re.IGNORECASE|re.DOTALL)
        editionPattern = re.compile("(es\.\s+\d+\/\d+)", re.IGNORECASE|re.DOTALL)
        sizePattern1 = re.compile("Largh\.?\s+([\d\.]+)\s+\-?\s+Prof\.?\s+([\d\.]+)\s+\-\s+Alt\.?\s+([\d\.]+)\s+(\w{2})", re.DOTALL)
        sizePattern2 = re.compile("Largh\.?\s+([\d\.]+)\s+\-?\s+Prof\.?\s+([\d\.]+)\s+(\w{2})", re.DOTALL)
        sizePattern3 = re.compile("Largh\.?\s+([\d\.]+)\s+\-\s+Alt\.?\s+([\d\.]+)\s+(\w{2})", re.DOTALL)
        descriptionPattern = re.compile("descrizione_lotto")
        cardbodyPattern = re.compile("card\-body")
        soup = BeautifulSoup(detailsPage, features="html.parser")
        descdivtags = soup.find_all("div", {'id' : 'descLotto'})
        if descdivtags.__len__() == 0:
            descdivtags = soup.find_all("div", {'class' : descriptionPattern})
        if descdivtags.__len__() > 0:
            descdivcontents = descdivtags[0].renderContents().decode('utf-8')
            descdivcontentparts = re.split(brPattern, descdivcontents)
            for desccontent in descdivcontentparts:
                cps = re.search(literaturePattern, desccontent)
                literature = desccontent
                litparts = literature.split("Provenienza")
                if litparts.__len__() > 0:
                    pass
                    #detailData['artwork_literature'] = litparts[0]
                    #detailData['artwork_literature'] = detailData['artwork_literature'].replace("\n", " ").replace("\r", "")
                    #detailData['artwork_literature'] = detailData['artwork_literature'].replace('"', "'")
                    #detailData['artwork_literature'] = beginspacePattern.sub("", detailData['artwork_literature'])
                if litparts.__len__() > 1:
                    detailData['artwork_provenance'] = litparts[1]
                    detailData['artwork_provenance'] = detailData['artwork_provenance'].replace("\n", " ").replace("\r", "")
                    detailData['artwork_provenance'] = detailData['artwork_provenance'].replace('"', "'")
                    detailData['artwork_provenance'] = beginspacePattern.sub("", detailData['artwork_provenance'])
                edps = re.search(editionPattern, desccontent)
                if edps:
                    detailData['artwork_edition'] = desccontent
            descdivcontents = self.__class__.htmltagPattern.sub("", descdivcontents)
            detailData['artwork_description'] = descdivcontents
            detailData['artwork_description'] = detailData['artwork_description'].replace("\n", " ").replace("\r", "")
            detailData['artwork_description'] = detailData['artwork_description'].replace('"', "'")
            detailData['artwork_description'] = beginspacePattern.sub("", detailData['artwork_description'])
            detailData['artwork_description'] = detailData['artwork_description'].replace("PROVENANCE", "<br><strong>Provenance</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("LITERATURE", "<br><strong>Literature</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("EXHIBITED", "<br><strong>Exhibited</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("EXPOSITIONS", "<br><strong>Expositions</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("BIBLIOGRAPHIE", "<br><strong>Literature</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("Condition Report", "<br><strong>Condition Report</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("Notes:", "<br><strong>Notes:</strong><br>")
            detailData['artwork_description'] = "<strong><br>Description<br></strong>" + detailData['artwork_description']
            detailData['artwork_description'] = detailData['artwork_description'].replace('"', "'")
        zps1 = re.search(sizePattern1, detailsPage)
        zps2 = re.search(sizePattern2, detailsPage)
        zps3 = re.search(sizePattern3, detailsPage)
        if zps1:
            detailData['artwork_measurements_height'] = zps1.groups()[0]
            detailData['artwork_measurements_width'] = zps1.groups()[1]
            detailData['artwork_measurements_depth'] = zps1.groups()[2]
            detailData['auction_measureunit'] = zps1.groups()[3]
            detailData['artwork_size_notes'] = detailData['artwork_measurements_height'] + " x " + detailData['artwork_measurements_width'] + " x " + detailData['artwork_measurements_depth'] + " " + detailData['auction_measureunit']
        elif zps2:
            detailData['artwork_measurements_height'] = zps2.groups()[0]
            detailData['artwork_measurements_width'] = zps2.groups()[1]
            detailData['auction_measureunit'] = zps2.groups()[2]
            detailData['artwork_size_notes'] = detailData['artwork_measurements_height'] + " x " + detailData['artwork_measurements_width'] + " " + detailData['auction_measureunit']
        elif zps3:
            detailData['artwork_measurements_height'] = zps3.groups()[0]
            detailData['artwork_measurements_width'] = zps3.groups()[1]
            detailData['auction_measureunit'] = zps3.groups()[2]
            detailData['artwork_size_notes'] = detailData['artwork_measurements_height'] + " x " + detailData['artwork_measurements_width'] + " " + detailData['auction_measureunit']
        if 'artwork_provenance' not in detailData.keys() or detailData['artwork_provenance'] == "":
            cardbodydivtags = soup.find_all("div", {'class' : cardbodyPattern})
            for cardbodydiv in cardbodydivtags:
                cardbodytext = cardbodydiv.renderContents().decode('utf-8')
                cardbodytext = self.__class__.htmltagPattern.sub("", cardbodytext)
                cardbodytext = cardbodytext.replace("\n", "").replace("\r", "")
                cps = re.search(literaturePattern, cardbodytext)
                if cps:
                    pass
                    #detailData['artwork_literature'] = cardbodytext
                    #detailData['artwork_literature'] = beginspacePattern.sub("", detailData['artwork_literature'])
                pps = re.search(provenancePattern, cardbodytext)
                if pps:
                    detailData['artwork_provenance'] = cardbodytext
                    detailData['artwork_provenance'] = beginspacePattern.sub("", detailData['artwork_provenance'])
        imagedivtags = soup.find_all("div", {'id' : 'tmpSlideshow'})
        if imagedivtags.__len__() == 0:
            imagedivtags = soup.find_all("div", {'id' : 'carousel'})
        if imagedivtags.__len__() == 0:
            imagedivtags = soup.find_all("div", {'class' : 'stageImg'})
        if imagedivtags.__len__() > 0:
            allimagetags = imagedivtags[0].find_all("a")
            if allimagetags.__len__() > 0:
                imageurl = allimagetags[0]['href']
                imagename1 = self.getImagenameFromUrl(imageurl)
                imagename1 = str(imagename1)
                imagename1 = imagename1.replace("b'", "").replace("'", "")
                auctiontitle = self.auctiontitle.replace(" ", "_")
                processedAuctionTitle = auctiontitle.replace(" ", "_")
                artistname = beginspacePattern.sub("", artistname)
                artistname = endspacePattern.sub("", artistname)
                lot_number = beginspacePattern.sub("", lot_number)
                lot_number = endspacePattern.sub("", lot_number)
                processedArtistName = artistname.replace(" ", "_")
                processedArtistName = unidecode.unidecode(processedArtistName)
                processedArtworkName = artwork_name.replace(" ", "_")
                sublot_number = ""
                #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + auction_number + "__" + lot_number + "__" + sublot_number
                newname1 = auction_number + "__" + processedArtistName + "__" + lot_number + "_a"
                #encryptedFilename = self.encryptFilename(newname1)
                encryptedFilename = newname1
                imagepathparts = imageurl.split("/")
                defimageurl = "/".join(imagepathparts[:-2])
                encryptedFilename = str(encryptedFilename).replace("b'", "")
                encryptedFilename = str(encryptedFilename).replace("'", "")
                detailData['image1_name'] = str(encryptedFilename) + ".jpg"
                detailData['artwork_images1'] = imageurl
                self.getImage(detailData['artwork_images1'], imagepath, downloadimages)
                if downloadimages == "1":
                    encryptedFilename = str(encryptedFilename) + "-a.jpg"
                    self.renameImageFile(imagepath, imagename1, encryptedFilename)
            imgctr = 2
            if allimagetags.__len__() > 1:
                imgurl2 = allimagetags[1]['href']
                altimage2parts = imgurl2.split("/")
                altimageurl = "/".join(altimage2parts[:-2])
                artistname = artistname.strip()
                artistname = beginspacePattern.sub("", artistname)
                artistname = endspacePattern.sub("", artistname)
                lot_number = beginspacePattern.sub("", lot_number)
                lot_number = endspacePattern.sub("", lot_number)
                processedArtistName = artistname.replace(" ", "_")
                processedArtistName = unidecode.unidecode(processedArtistName)
                processedArtworkName = artwork_name.replace(" ", "_")
                sublot_number = ""
                lot_number = lot_number.strip()
                #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + auction_number + "__" + lot_number + "__" + sublot_number
                newname1 = auction_number + "__" + processedArtistName + "__" + lot_number + "_b"
                #encryptedFilename = self.encryptFilename(newname1)
                encryptedFilename = newname1
                encryptedFilename = str(encryptedFilename).replace("b'", "")
                encryptedFilename = str(encryptedFilename).replace("'", "")
                detailData['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
                detailData['artwork_images' + str(imgctr)] = imgurl2
                self.getImage(detailData['artwork_images' + str(imgctr)], imagepath, downloadimages)
                if downloadimages == "1":
                    encryptedFilename = str(encryptedFilename) + "-b.jpg"
                    self.renameImageFile(imagepath, imagename1, encryptedFilename)
                imgctr += 1
            if allimagetags.__len__() > 2:
                imgurl3 = allimagetags[2]['href']
                altimage3parts = imgurl3.split("/")
                altimageurl = "/".join(altimage3parts[:-2])
                detailData['image' + str(imgctr) + '_name'] = self.getImagenameFromUrl(imgurl3)
                artistname = beginspacePattern.sub("", artistname)
                artistname = endspacePattern.sub("", artistname)
                lot_number = beginspacePattern.sub("", lot_number)
                lot_number = endspacePattern.sub("", lot_number)
                processedArtistName = artistname.replace(" ", "_")
                processedArtistName = unidecode.unidecode(processedArtistName)
                processedArtworkName = artwork_name.replace(" ", "_")
                sublot_number = ""
                #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + auction_number + "__" + lot_number + "__" + sublot_number
                newname1 = auction_number + "__" + processedArtistName + "__" + lot_number + "_c"
                #encryptedFilename = self.encryptFilename(newname1)
                encryptedFilename = newname1
                encryptedFilename = str(encryptedFilename).replace("b'", "")
                encryptedFilename = str(encryptedFilename).replace("'", "")
                detailData['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
                detailData['artwork_images' + str(imgctr)] = imgurl3
                self.getImage(detailData['artwork_images' + str(imgctr)], imagepath, downloadimages)
                if downloadimages == "1":
                    encryptedFilename = str(encryptedFilename) + "-d.jpg"
                    self.renameImageFile(imagepath, imagename1, encryptedFilename)
                imgctr += 1
            if allimagetags.__len__() > 3:
                imgurl4 = allimagetags[3]['href']
                altimage4parts = imgurl4.split("/")
                altimageurl = "/".join(altimage4parts[:-2])
                detailData['image' + str(imgctr) + '_name'] = self.getImagenameFromUrl(imgurl4)
                artistname = beginspacePattern.sub("", artistname)
                artistname = endspacePattern.sub("", artistname)
                lot_number = beginspacePattern.sub("", lot_number)
                lot_number = endspacePattern.sub("", lot_number)
                processedArtistName = artistname.replace(" ", "_")
                processedArtistName = unidecode.unidecode(processedArtistName)
                processedArtworkName = artwork_name.replace(" ", "_")
                sublot_number = ""
                #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + auction_number + "__" + lot_number + "__" + sublot_number
                newname1 = auction_number + "__" + processedArtistName + "__" + lot_number + "_d"
                #encryptedFilename = self.encryptFilename(newname1)
                encryptedFilename = newname1
                encryptedFilename = str(encryptedFilename).replace("b'", "")
                encryptedFilename = str(encryptedFilename).replace("'", "")
                detailData['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
                detailData['artwork_images' + str(imgctr)] = imgurl4
                self.getImage(detailData['artwork_images' + str(imgctr)], imagepath, downloadimages)
                if downloadimages == "1":
                    encryptedFilename = str(encryptedFilename) + "-e.jpg"
                    self.renameImageFile(imagepath, imagename1, encryptedFilename)
                imgctr += 1
        return detailData


    def getImage(self, imageUrl, imagepath, downloadimages):
        imageUrlParts = imageUrl.split("/")
        imagefilename = imageUrlParts[-1]
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


    def getInfoFromLotsData(self, htmlList, imagepath, downloadimages):
        baseUrl = "https://www.cambiaste.com"
        info = []
        endSpacePattern = re.compile("\s+$", re.DOTALL)
        soldpricePattern = re.compile("([\d\s\.,]+)\s+€")
        beginspacePattern = re.compile("^\s+")
        sizePattern = re.compile("cm\s+([\d\sx\.,]+)", re.DOTALL)
        sizePattern2 = re.compile("in\s+([\d\sx\.,]+)", re.DOTALL)
        sizePattern3 = re.compile("(\w{2})\s+([\d\sx\.,]+)", re.DOTALL)
        sizePattern4 = re.compile("(Largh\.\s+[\d]+\s*\-\s*Alt\.\s+[\d]+)\s+(\w{2})", re.IGNORECASE|re.DOTALL)
        sizePattern5 = re.compile("(\w{2})\s*([\d\.,]+)\s*x\s*([\d\.,]+)\s*", re.DOTALL)
        sizePattern6 = re.compile("Largh\.?\s+([\d\.]+)\s+\-?\s+Prof\.?\s+([\d\.]+)\s+\-\s+Alt\.?\s+([\d\.]+)\s+(\w{2})", re.DOTALL)
        euroPattern = re.compile("€", re.DOTALL)
        euroPattern2 = re.compile("&euro;", re.IGNORECASE|re.DOTALL)
        dollarPattern = re.compile("\$", re.DOTALL)
        gbpPattern = re.compile("£", re.DOTALL)
        yearPattern = re.compile("(\d{4})")
        infoPattern = re.compile("([^(]+)\s+\((\d{4})\-?(\d{0,4})\)", re.DOTALL)
        titlePattern = re.compile("[\w\s\-\,\.]+\(\d{4}\s*\-\s*\d{0,4}\)\s+(.*)$", re.DOTALL)
        titlePattern1 = re.compile("([\w\s\.]+)\s+\(([\w]*)\,?\s*(\d{4})[\-\s–]+[\w\s,]*(\d{4})\)(.*)$")
        centuryPattern = re.compile("^(.*century)|(.*secolo)\s+(.*)$", re.IGNORECASE|re.DOTALL)
        matcatdict_en = {}
        matcatdict_fr = {}
        #with open("docs/fineart_materials.csv", newline='') as mapfile:
        with open("/root/artwork/deploydirnew/docs/fineart_materials.csv", newline='') as mapfile:
            mapreader = csv.reader(mapfile, delimiter=",", quotechar='"')
            for maprow in mapreader:
                matcatdict_en[maprow[1]] = maprow[3]
                matcatdict_fr[maprow[2]] = maprow[3]
        mapfile.close()
        for htmldiv in htmlList:
            data = {}
            data['lot_num'], data['artist_name'], data['artist_birth'], data['artist_death'], data['artwork_name'], data['artwork_measurements_height'], data['artwork_measurements_width'], data['artwork_measurements_depth'], data['artwork_materials'], data['price_estimate_min'], data['price_estimate_max'], data['price_sold'] = "", "", "", "", "", "", "", "", "", "", "", ""
            data['auction_num'] = self.saleno
            data['auction_location'] = self.auctionlocation
            data['auction_name'] = self.auctiontitle
            self.auctiondate = endSpacePattern.sub("", self.auctiondate)
            self.auctiondate = beginspacePattern.sub("", self.auctiondate)
            data['auction_start_date'] = self.auctiondate
            data['auction_house_name'] = "Cambiaste"
            lotno = ""
            htmlContent = htmldiv.renderContents().decode('utf-8')
            s = BeautifulSoup(htmlContent, features="html.parser")
            lotdivtags = s.find_all("div", {'class' : 'number'})
            if lotdivtags.__len__() > 0:
                lotno = lotdivtags[0].renderContents().decode('utf-8')
                lotno = lotno.replace("\n", "").replace("\r", "")
            if not lotno:
                continue
            data['lot_num'] = lotno
            allanchors = s.find_all("a")
            htmlanchor = allanchors[0]
            detailUrl = htmlanchor['href']
            data['lot_origin_url'] = detailUrl
            anchorcontent = htmlanchor.renderContents().decode('utf-8')
            anchorcontent = anchorcontent.replace("\n", "").replace("\r", "")
            ips = re.search(infoPattern, anchorcontent)
            if ips:
                ipsg = ips.groups()
                data['artist_name'] = ipsg[0]
                data['artist_birth'] = ipsg[1].replace("\n", "").replace("\r", "")
                data['artist_death'] = ipsg[2].replace("\n", "").replace("\r", "")
            else:
                pass
            if 'artist_name' in data.keys():
                data['artist_name'] = data['artist_name'].replace(" (née en", "").replace(" (né en", "")
                data['artist_name'] = data['artist_name'].replace("¤ ", "")
                data['artist_name'] = data['artist_name'].replace('"', "'")
                data['artist_name'] = data['artist_name'].replace("<img alt='", "").replace("\n", "").replace("\r", "")
            titledivtags = s.find_all("div", {'class' : 'titleOpera'})
            if titledivtags.__len__() > 0:
                titlecontents = titledivtags[0].renderContents().decode('utf-8')
                titlecontents = self.__class__.htmltagPattern.sub("", titlecontents)
                titlecontents = titlecontents.replace("\n", "").replace("\r", "")
                titlecontents = titlecontents.replace('"', "'")
                titlecontents = beginspacePattern.sub("", titlecontents)
                tps = re.search(titlePattern, titlecontents)
                tps1 = re.search(titlePattern1, titlecontents)
                if tps:
                    data['artwork_name'] = tps.groups()[0]
                elif tps1:
                    if 'artist_name' not in data.keys() or data['artist_name'] == "":
                        data['artist_name'] = tps1.groups()[0]
                    if 'artist_birth' not in data.keys() or data['artist_birth'] == "":
                        data['artist_birth'] = tps1.groups()[2]
                    if 'artist_death' not in data.keys() or data['artist_death'] == "":
                        data['artist_death'] = tps1.groups()[3]
                    if 'artist_nationality' not in data.keys() or data['artist_nationality'] == "":
                        data['artist_nationality'] = tps1.groups()[1]
                    data['artwork_name'] = tps1.groups()[4]
                else:
                    data['artwork_name'] = titlecontents
                    cps = re.search(centuryPattern, titlecontents)
                    if cps:
                        cpsg = cps.groups()
                        if cpsg[0]:
                            data['artist_name'] = cpsg[0]
                        elif cpsg[1]:
                            data['artist_name'] = cpsg[1]
                        data['artwork_name'] = cpsg[2]
                yps = re.search(yearPattern, titlecontents)
                if yps and not tps1:
                    data['artwork_start_year'] = yps.groups()[0]
            descdivtags = s.find_all("div", {'class' : 'descLotto'})
            if descdivtags.__len__() == 0:
                descdivtags = s.find_all("div", {'class' : 'desc py-4'})
            if descdivtags.__len__() > 0:
                desctext = descdivtags[0].renderContents().decode('utf-8')
                zps = re.search(sizePattern, desctext)
                if zps:
                    size = zps.groups()[0]
                    size = size.replace(",", ".")
                    sizeparts = size.split("x")
                    if sizeparts.__len__() > 0:
                        data['artwork_measurements_height'] = sizeparts[0]
                    if sizeparts.__len__() > 1:
                        data['artwork_measurements_width'] = sizeparts[1]
                    if sizeparts.__len__() > 2:
                        data['artwork_measurements_depth'] = sizeparts[2]
                    data['auction_measureunit'] = "cm"
                zps2 = re.search(sizePattern2, desctext)
                if zps2:
                    size = zps2.groups()[0]
                    size = size.replace(",", ".")
                    sizeparts = size.split("x")
                    if sizeparts.__len__() > 0:
                        data['artwork_measurements_height'] = sizeparts[0]
                    if sizeparts.__len__() > 1:
                        data['artwork_measurements_width'] = sizeparts[1]
                    if sizeparts.__len__() > 2:
                        data['artwork_measurements_depth'] = sizeparts[2]
                    data['auction_measureunit'] = "in"
                zps5 = re.search(sizePattern5, desctext)
                if zps5:
                    data['auction_measureunit'] = zps5.groups()[0]
                    data['artwork_measurements_height'] = zps5.groups()[1]
                    data['artwork_measurements_width'] = zps5.groups()[2]
                    data['artwork_size_notes'] = data['artwork_measurements_height'] + " x " + data['artwork_measurements_width'] + " " + data['auction_measureunit']
                desctextparts = desctext.split(",")
                if desctextparts.__len__() > 0:
                    desctextparts[0] = beginspacePattern.sub("", desctextparts[0])
                    data['artwork_materials'] = desctextparts[0]
                if desctextparts.__len__() > 1:
                    desctextparts[1] = sizePattern.sub("", desctextparts[1])
                    desctextparts[1] = sizePattern2.sub("", desctextparts[1])
                    desctextparts[1] = beginspacePattern.sub("", desctextparts[1])
                    data['artwork_materials'] += ", " +  desctextparts[1]
            if 'artwork_materials' in data.keys() and 'artwork_category' not in data.keys():
                data['artwork_materials'] = data['artwork_materials'].replace("\n", "").replace("\r", "")
                data['artwork_materials'] = beginspacePattern.sub("", data['artwork_materials'])
                data['artwork_materials'] = data['artwork_materials'].replace("&lt;", "<").replace("&gt;", ">")
                data['artwork_materials'] = self.__class__.htmltagPattern.sub("", data['artwork_materials'])
                zps3 = re.search(sizePattern3, data['artwork_materials'])
                zps4 = re.search(sizePattern4, data['artwork_materials'])
                if zps3:
                    data['auction_measureunit'] = zps3.groups()[0]
                    data['auction_measureunit'] = beginspacePattern.sub("", data['auction_measureunit'])
                    size = zps3.groups()[1]
                    sizeparts = size.split("x")
                    if sizeparts.__len__() == 2:
                        data['artwork_measurements_height'] = sizeparts[0]
                        data['artwork_measurements_width'] = sizeparts[1]
                        data['artwork_measurements_depth'] = ""
                    if sizeparts.__len__() == 3:
                        data['artwork_measurements_height'] = sizeparts[0]
                        data['artwork_measurements_width'] = sizeparts[1]
                        data['artwork_measurements_depth'] = sizeparts[2]
                    data['artwork_size_notes'] = size + " " + data['auction_measureunit']
                    data['artwork_size_notes'] = beginspacePattern.sub("", data['artwork_size_notes'])
                    data['artwork_materials'] = sizePattern3.sub("", data['artwork_materials'])
                if zps4:
                    size = zps4.groups()[0]
                    data['auction_measureunit'] = zps4.groups()[1]
                    data['auction_measureunit'] = beginspacePattern.sub("", data['auction_measureunit'])
                    sizeparts = size.split("-")
                    if sizeparts.__len__() == 2:
                        data['artwork_measurements_height'] = sizeparts[0]
                        data['artwork_measurements_width'] = sizeparts[1]
                        data['artwork_measurements_depth'] = ""
                    if sizeparts.__len__() == 3:
                        data['artwork_measurements_height'] = sizeparts[0]
                        data['artwork_measurements_width'] = sizeparts[1]
                        data['artwork_measurements_depth'] = sizeparts[2]
                    data['artwork_size_notes'] = size + " " + data['auction_measureunit']
                    data['artwork_size_notes'] = beginspacePattern.sub("", data['artwork_size_notes'])
                    data['artwork_materials'] = sizePattern4.sub("", data['artwork_materials'])
                data['artwork_materials'] = data['artwork_materials'].replace("(foglio)", "").replace("(rame)", "")
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
            estimatedivtags = s.find_all("div", {'class' : 'estimate'})
            if estimatedivtags.__len__() == 0:
                estimatedivtags = s.find_all("div", {'class' : 'estimate2'})
            if estimatedivtags.__len__() > 0:
                estimatecontent = estimatedivtags[0].renderContents().decode('utf-8')
                esp = re.search(euroPattern, estimatecontent)
                estimate = ""
                currency = " USD"
                if esp:
                    currency = " EUR"
                    estimate = euroPattern.sub("", estimatecontent)
                esp2 = re.search(euroPattern2, estimatecontent)
                if esp2:
                    currency = " EUR"
                    estimate = euroPattern2.sub("", estimatecontent)
                gsp = re.search(gbpPattern, estimatecontent)
                if gsp:
                    currency = " GBP"
                    estimate = gbpPattern.sub("", estimatecontent)
                dsp = re.search(dollarPattern, estimatecontent)
                if dsp:
                    currency = " USD"
                    estimate = dollarPattern.sub("", estimatecontent)
                estimate = self.__class__.htmltagPattern.sub("", estimate)
                estimate = estimate.replace("\n", "").replace("\r", "")
                estimate = estimate.replace("Estimate", "")
                estimateparts = estimate.split("-")
                if "/" in estimate:
                    estimateparts = estimate.split("/")
                if estimateparts.__len__() > 0:
                    data['price_estimate_min'] = estimateparts[0]
                    data['price_estimate_min'] = beginspacePattern.sub("", data['price_estimate_min'])
                if estimateparts.__len__() > 1:
                    data['price_estimate_max'] = estimateparts[1]
                    data['price_estimate_max'] = beginspacePattern.sub("", data['price_estimate_max'])
            soldpricedivtags = s.find_all("b", {'class' : 'venduto'})
            if soldpricedivtags.__len__() > 0:
                soldpricecontents = soldpricedivtags[0].renderContents().decode('utf-8')
                soldpricecontents = soldpricecontents.replace("&nbsp;", " ")
                soldcurrency = " USD"
                sesp = re.search(euroPattern, soldpricecontents)
                soldprice = ""
                if sesp:
                    currency = " EUR"
                    soldprice = euroPattern.sub("", soldpricecontents)
                sgsp = re.search(gbpPattern, soldpricecontents)
                if sgsp:
                    currency = " GBP"
                    soldprice = gbpPattern.sub("", soldpricecontents)
                else:
                    currency = " USD"
                    soldprice = dollarPattern.sub("", soldpricecontents)
                #soldprice += currency
                soldprice = soldprice.replace("sold €", "").replace("sold £", "").replace("sold $", "")
                soldprice = self.__class__.htmltagPattern.sub("", soldprice)
                soldprice = soldprice.replace("\n", "").replace("\r", "")
                data['price_sold'] = soldprice
            withdrawnPattern = re.compile("withdrawn", re.IGNORECASE|re.DOTALL)
            data['price_kind'] = "unknown"
            if re.search(withdrawnPattern, data['price_sold']) or re.search(withdrawnPattern, data['price_estimate_max']):
                data['price_kind'] = "withdrawn"
            elif 'price_sold' in data.keys() and data['price_sold'] != "":
                data['price_kind'] = "price realized"
            elif 'price_estimate_max' in data.keys() and data['price_estimate_max'] != "":
                data['price_kind'] = "estimate"
            else:
                pass
            #print(data['lot_num'] + " ## " + data['artist_name'] + " ## " + data['artist_birth'] + " ## " + data['artist_death'] + " ## " + data['price_estimate_min'] + " ## " + data['price_estimate_max'] + " ## " + data['price_sold'] + " ## " + data['auction_location'] + " ## " + data['auction_name'] + " ## " + data['auction_start_date'] + " ## " + data['price_kind'] + " ## " + data['artwork_measurements_height'] + " ## " + data['artwork_measurements_width'] + " ## " + data['artwork_measurements_depth'] + " ## " + data['auction_measureunit'])
            print("Getting '%s'..."%data['lot_origin_url'])
            detailsPageContent = self.getDetailsPage(detailUrl)
            if not lotno:
                continue
            detailData = self.parseDetailPage(detailsPageContent, data['artist_name'], data['artwork_name'], self.saleno, lotno, imagepath, downloadimages)
            for k in detailData.keys():
                data[k] = detailData[k]
            if 'price_sold' not in data.keys() or data['price_sold'] == "":
                data['price_sold'] = ""
            if 'artwork_size_notes' in data.keys():
                if 'artwork_measurements_height' in data.keys():
                    data['artwork_measurements_height'] = data['artwork_measurements_height'].replace("\n", "").replace("\r", "")
                if 'artwork_measurements_width' in data.keys():
                    data['artwork_measurements_width'] = data['artwork_measurements_width'].replace("\n", "").replace("\r", "")
                if 'artwork_measurements_depth' in data.keys():
                    data['artwork_measurements_depth'] = data['artwork_measurements_depth'].replace("\n", "").replace("\r", "")
                data['artwork_size_notes'] = data['artwork_size_notes'].replace("\n", "").replace("\r", "")
            if 'artwork_description' in data.keys():
                if 'artwork_name' in data.keys():
                    data['artwork_description'] += "Artwork Name: " + str(data['artwork_name'])
                if 'artist_name' in data.keys():
                    data['artwork_description'] += "Artist Name: " + str(data['artist_name'])
                if 'artwork_materials' in data.keys():
                    data['artwork_description'] += " " + str(data['artwork_materials'])
                if 'artwork_size_notes' in data.keys():
                    data['artwork_description'] += " Size: " + data['artwork_size_notes']
                if 'artwork_materials' in data.keys():
                    data['artwork_description'] += " Materials: " + data['artwork_materials']
                if 'artwork_markings' in data.keys():
                    data['artwork_description'] += " Markings: " + data['artwork_markings']
                if 'price_estimate_min' in data.keys():
                    data['artwork_description'] += " Min Estimate: " + data['price_estimate_min']
                if 'price_estimate_max' in data.keys():
                    data['artwork_description'] += " Max Estimate: " + data['price_estimate_max']
                if 'price_sold' in data.keys():
                    data['artwork_description'] += " Sold Price: " + data['price_sold']
            if 'price_estimate_min' in data.keys():
                data['price_estimate_min'] = data['price_estimate_min'].replace(",", "").replace(" ", "")
            if 'price_estimate_max' in data.keys():
                data['price_estimate_max'] = data['price_estimate_max'].replace(",", "").replace(" ", "")
            if 'price_sold' in data.keys():
                data['price_sold'] = data['price_sold'].replace(",", "").replace(" ", "")
            dateparts = self.auctiondate.split("/")
            if dateparts.__len__() > 2:
                yy = dateparts[2][2:]
                mondict = {'01' : 'Jan', '02' : 'Feb', '03' : 'Mar', '04' : 'Apr', '05' : 'May', '06' : 'Jun', '07' : 'Jul', '08' : 'Aug', '09' : 'Sep', '10' : 'Oct', '11' : 'Nov', '12' : 'Dec'}
                mmm = mondict[dateparts[1]]
                dd = dateparts[0]
                data['auction_start_date'] = "%s-%s-%s"%(dd, mmm, yy)
            info.append(data)
        return info


    def getNextPage(self, chunksize, offset, requestUrl, auctionurl, auctionnumber):
        headers = {'Accept' : '*/*', 'Accept-Encoding' : 'gzip, deflate, br', 'Accept-Language' : 'en-GB,en-US;q=0.9,en;q=0.8', 'Content-Type' : 'application/x-www-form-urlencoded; charset=UTF-8', 'Host' : 'www.cambiaste.com', 'Origin' : 'https://www.cambiaste.com', 'Referer' : auctionurl, 'Sec-Fetch-Dest' : 'empty', 'Sec-Fetch-Mode' : 'cors', 'Sec-Fetch-Site' : 'same-origin', 'User-Agent' : 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36', 'X-Requested-With' : 'XMLHttpRequest'}
        postdata = "ajx=1&idAsta=704&sesN=auction-%s&cat=&cat2=&aut=&amt=&ordB=lot&htmlI=&tipA=False&ven=True&inVen=False&usr=&arc=True&charStr=iso-8859-1&limit=%s&offset=%s&lan=uk&deb="%(auctionnumber, str(chunksize), str(offset))
        contentlen = postdata.__len__()
        postdatabytes = bytes(postdata, 'utf-8')
        headers['Content-Length'] = contentlen
        request = urllib.request.Request(requestUrl, postdatabytes, headers=headers)
        pageResponse = None
        try:
            pageResponse = self.opener.open(request)
        except:
            print ("Error: %s"%sys.exc_info()[1].__str__())
        pagecontent = self.__class__._decodeGzippedContent(pageResponse.read())
        return pagecontent

"""
[
'auction_house_name', 'auction_location', 'auction_num', 'auction_start_date', 'auction_end_date', 'auction_name', 'lot_num', 'sublot_num', 'price_kind', 'price_estimate_min', 'price_estimate_max', 'price_sold', 'artist_name', 'artist_birth', 'artist_death', 'artist_nationality', 'artwork_name', 'artwork_year_identifier', 'artwork_start_year', 'artwork_end_year', 'artwork_materials', 'artwork_category', 'artwork_markings', 'artwork_edition', 'artwork_description', 'artwork_measurements_height', 'artwork_measurements_width', 'artwork_measurements_depth', 'artwork_size_notes', 'auction_measureunit', 'artwork_condition_in', 'artwork_provenance', 'artwork_exhibited', 'artwork_literature', 'artwork_images1', 'artwork_images2', 'artwork_images3', 'artwork_images4', 'artwork_images5', 'image1_name', 'image2_name', 'image3_name', 'image4_name', 'image5_name', 'lot_origin_url'
]
 """

# That's it.... 

def updatestatus(auctionno, auctionurl):
    auctionurl = auctionurl.replace("%3A", ":")
    auctionurl = auctionurl.replace("%2F", "/")
    pageurl = "http://216.137.189.57:8080/scrapers/finish/?scrapername=Cambiaste&auctionnumber=%s&auctionurl=%s&scrapertype=2"%(auctionno, urllib.parse.quote(auctionurl))
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
    cambiaste = CambiasteBot(auctionurl, auctionnumber)
    fp = open(csvpath, "w")
    fieldnames = ['auction_house_name', 'auction_location', 'auction_num', 'auction_start_date', 'auction_end_date', 'auction_name', 'lot_num', 'sublot_num', 'price_kind', 'price_estimate_min', 'price_estimate_max', 'price_sold', 'artist_name', 'artist_birth', 'artist_death', 'artist_nationality', 'artwork_name', 'artwork_year_identifier', 'artwork_start_year', 'artwork_end_year', 'artwork_materials', 'artwork_category', 'artwork_markings', 'artwork_edition', 'artwork_description', 'artwork_measurements_height', 'artwork_measurements_width', 'artwork_measurements_depth', 'artwork_size_notes', 'auction_measureunit', 'artwork_condition_in', 'artwork_provenance', 'artwork_exhibited', 'artwork_literature', 'artwork_images1', 'artwork_images2', 'artwork_images3', 'artwork_images4', 'artwork_images5', 'image1_name', 'image2_name', 'image3_name', 'image4_name', 'image5_name', 'lot_origin_url']
    fieldsstr = ",".join(fieldnames)
    fp.write(fieldsstr + "\n")
    offset = 0
    chunksize = 30
    pagectr = 1
    lastlotscount = 0
    while True:
        soup = BeautifulSoup(cambiaste.currentPageContent, features="html.parser")
        lotsdata = cambiaste.getLotsFromPage()
        if lotsdata.__len__() == lastlotscount and lotsdata.__len__() < chunksize:
            break
        lastlotscount = lotsdata.__len__()
        info = cambiaste.getInfoFromLotsData(lotsdata, imagepath, downloadimages)
        lotctr = 0 
        for d in info:
            lotctr += 1
            for f in fieldnames:
                if f in d and d[f] is not None:
                    fp.write('"' + str(d[f]) + '",')
                else:
                    fp.write('"",')
            fp.write("\n")
        offset += 30
        #requestUrl = "https://www.cambiaste.com/include/inc-basket-lots-list-infinite-view.asp"
        urlparts = auctionurl.split("?")
        pagectr += 1
        requestUrl = urlparts[0] + "?pag=" + str(pagectr) + "#catalogue"
        #cambiaste.currentPageContent = cambiaste.getNextPage(chunksize, offset, requestUrl, auctionurl, auctionnumber)
        cambiaste.pageRequest = urllib.request.Request(requestUrl, headers=cambiaste.httpHeaders)
        try:
            cambiaste.pageResponse = cambiaste.opener.open(cambiaste.pageRequest)
        except:
            print("Couldn't find the page %s"%str(pagectr))
            break
        cambiaste.currentPageContent = cambiaste.__class__._decodeGzippedContent(cambiaste.getPageContent())
    fp.close()
    updatestatus(auctionnumber, auctionurl)

# Example: python cambiaste.py https://www.cambiaste.com/uk/auction-0604-2/modern-and-contemporary-art.asp?action=reset 0604-2 /home/supmit/work/art2/cambiaste_0604-2.csv /home/supmit/work/art2/images/cambiaste/0604-2 0 0



# supmit

