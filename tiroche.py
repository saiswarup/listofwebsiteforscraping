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


class TirocheBot(object):
    
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
        self.httpHeaders = { 'User-Agent' : r'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36',  'Accept' : 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8', 'Accept-Language' : 'en-us,en;q=0.5', 'Accept-Encoding' : 'gzip,deflate', 'Accept-Charset' : 'ISO-8859-1,utf-8;q=0.7,*;q=0.7', 'Keep-Alive' : '115', 'Connection' : 'keep-alive', }
        self.httpHeaders['Cache-Control'] = "no-cache"
        self.httpHeaders['upgrade-insecure-requests'] = "1"
        self.httpHeaders['sec-fetch-dest'] = "document"
        self.httpHeaders['sec-fetch-mode'] = "navigate"
        self.httpHeaders['sec-fetch-site'] = "none"
        self.httpHeaders['sec-fetch-user'] = "?1"
        self.httpHeaders['Cookie'] = "splash_screen_disabled=true;"
        self.httpHeaders['Host'] = "www.tiroche.co.il"
        self.httpHeaders['Pragma'] = "no-cache"
        self.homeDir = os.getcwd()
        self.requestUrl = auctionurl
        parsedUrl = urlparse(self.requestUrl)
        self.baseUrl = parsedUrl.scheme + "://" + parsedUrl.netloc
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
        try:
            return(self.pageResponse.read())
        except:
            return(b"")

    def formatDate(cls, datestr):
        mondict = {'January' : '01', 'February' : '02', 'March' : '03', 'April' : '04', 'May' : '05', 'June' : '06', 'July' : '07', 'August' : '08', 'September' : '09', 'October' : '10', 'November' : '11', 'December' : '12' }
        mondict2 = {'Jan' : '01', 'Feb' : '02', 'Mar' : '03', 'Apr' : '04', 'May' : '05', 'Jun' : '06', 'Jul' : '07', 'Aug' : '08', 'Sep' : '09', 'Oct' : '10', 'Nov' : '11', 'Dec' : '12' }
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
                mm = mondict2[datestrcomponents[1]]
            except:
                pass
        yyyy = datestrcomponents[2]
        yearPattern = re.compile("\d{4}")
        if not re.search(yearPattern, yyyy):
            yyyy = "2021"
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
        #print(pageContent)
        soup = BeautifulSoup(pageContent, features="html.parser")
        timingtags = soup.find_all("span", {'class' : 'subtitle_date'})
        if timingtags.__len__() > 0:
            timingcontents = timingtags[0].renderContents().decode('utf-8')
            datePattern = re.compile("(\d{1,2}\s+[a-zA-Z]+)\s+\-.*?\s+(\d{4})")
            dps = re.search(datePattern, timingcontents)
            if dps:
                self.auctiondate = dps.groups()[0] + " " + dps.groups()[1]
        else:
            dateptag = soup.find("p", {'id' : 'dateTimeField'})
            if dateptag:
                dateval = dateptag['data-time']
                datevalparts = dateval.split("T")
                if datevalparts.__len__() > 0:
                    self.auctiondate = datevalparts[0]
        alltitletags = soup.find_all("title")
        if alltitletags.__len__() > 0:
            title = alltitletags[0].renderContents().decode('utf-8')
            titleparts = title.split("|")
            if titleparts.__len__() > 0:
                self.auctiontitle = titleparts[0]
                self.auctiontitle = self.auctiontitle.replace("Works - ", "")
                trailingspacePattern = re.compile("\s+$")
                self.auctiontitle = trailingspacePattern.sub("", self.auctiontitle)
        idPattern = re.compile("lot\-(\d+)", re.IGNORECASE) # You never know when they will change case... !
        liblocks = soup.find_all("div", {'id' : idPattern})
        if liblocks.__len__() > 0:
            return liblocks
        return []
        

    def getDetailsPage(self, detailUrl):
        self.requestUrl = detailUrl
        self.pageRequest = urllib.request.Request(self.requestUrl, headers=self.httpHeaders)
        self.pageResponse = None
        self.postData = {}
        try:
            self.pageResponse = self.opener.open(self.pageRequest)
        except:
            print ("Error: %s"%sys.exc_info()[1].__str__())
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
        baseUrl = "https://www.tiroche.co.il"
        detailData = {}
        soup = BeautifulSoup(detailsPage, features="html.parser")
        signedPattern = re.compile("signed\s+", re.IGNORECASE)
        editionPattern = re.compile("edition", re.IGNORECASE)
        yearPattern = re.compile("(\d{4})\s*\-?\s*(\d{0,4})", re.DOTALL)
        multispacePattern = re.compile("\s+")
        beginspacePattern = re.compile("^\s+")
        matcatdict_en = {}
        matcatdict_fr = {}
        #with open("docs/fineart_materials.csv", newline='') as mapfile:
        with open("/root/artwork/deploydirnew/docs/fineart_materials.csv", newline='') as mapfile:
            mapreader = csv.reader(mapfile, delimiter=",", quotechar='"')
            for maprow in mapreader:
                matcatdict_en[maprow[1]] = maprow[3]
                matcatdict_fr[maprow[2]] = maprow[3]
        mapfile.close()
        artistname = ""
        artistdivtag = soup.find("div", {'class' : 'single-lot__h1'})
        if artistdivtag:
            artistcontent = artistdivtag.renderContents().decode('utf-8')
            artistcontent = artistcontent.replace("\n", "").replace("\r", "")
            artistcontent = self.__class__.htmltagPattern.sub("", artistcontent)
            artistname = artistcontent
        estimateptag = soup.find("p", {'class' : 'single-lot__estimate mb-4'})
        estimatecontents = ""
        if estimateptag:
            estimatecontents = estimateptag.renderContents().decode('utf-8')
            estimatecontents = estimatecontents.replace("\n", "").replace("\r", "")
            estimatecontents = self.__class__.htmltagPattern.sub("", estimatecontents)
            estimatecontents = estimatecontents.replace("$", "").replace("Estimated price:", "")
            estimateparts = estimatecontents.split("-")
            detailData['price_estimate_min'] = estimateparts[0]
            detailData['price_estimate_min'] = beginspacePattern.sub("", detailData['price_estimate_min'])
            if estimateparts.__len__() > 1:
                detailData['price_estimate_max'] = estimateparts[1]
                detailData['price_estimate_max'] = beginspacePattern.sub("", detailData['price_estimate_max'])
        lotimagediv = soup.find("div", {'id' : 'lotImages'})
        defaultimageurl = ""
        if lotimagediv:
            imganchor = lotimagediv.find("a")
            if imganchor:
                defaultimageurl = imganchor['href']
        imagename1 = self.getImagenameFromUrl(defaultimageurl)
        imagename1 = str(imagename1)
        imagename1 = imagename1.replace("b'", "").replace("'", "")
        auctiontitle = self.auctiontitle.replace(" ", "_")
        processedAuctionTitle = auctiontitle.replace(" ", "_")
        processedArtistName = artistname.replace(" ", "_")
        processedArtistName = unidecode.unidecode(processedArtistName)
        newname1 = self.saleno + "__" + processedArtistName + "__" + lotno + "_a"
        encryptedFilename = newname1
        imagepathparts = defaultimageurl.split("/")
        defimageurl = "/".join(imagepathparts[:-2])
        encryptedFilename = str(encryptedFilename).replace("b'", "")
        encryptedFilename = str(encryptedFilename).replace("'", "")
        detailData['image1_name'] = str(encryptedFilename) + ".jpg"
        detailData['artwork_images1'] = defaultimageurl
        contentdiv = soup.find("div", {'class' : 'desc'})
        if contentdiv:
            divcontents = contentdiv.renderContents().decode('utf-8')
            divcontents = self.__class__.htmltagPattern.sub("", divcontents)
            divcontents = divcontents.replace("\n", "").replace("\r", "")
            divcontents = divcontents.replace('"', "'")
            detailData['artwork_description'] = divcontents + artistcontent + estimatecontents
            detailData['artwork_description'] = detailData['artwork_description'].replace("Provenance", "<br><strong>Provenance</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("Literature", "<br><strong>Literature</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("Exhibited", "<br><strong>Exhibited</strong><br>")
            detailData['artwork_description'] = "<strong><br>Description<br></strong>" + detailData['artwork_description']
        detailData['auction_house_name'] = "Tiroche"
        return detailData


    def getImage(self, imageUrl, imagepath, downloadimages):
        imageUrlParts = imageUrl.split("/")
        imagefilename = imageUrlParts[-2] + "_" + imageUrlParts[-1]
        imagedir = imageUrlParts[-2]
        backslashPattern = re.compile(r"\\")
        if downloadimages == "1":
            pageRequest = urllib.request.Request(imageUrl, headers=self.httpHeaders)
            pageResponse = None
            try:
                pageResponse = self.opener.open(pageRequest)
            except:
                print ("Error: %s"%sys.exc_info()[1].__str__())
            try:
                imageContent = pageResponse.read()
                imagefilename = backslashPattern.sub("_", imagefilename)
                ifp = open(imagepath + os.path.sep + imagefilename, "wb")
                ifp.write(imageContent)
                ifp.close()
                return imagefilename
            except:
                print("Error: %s"%sys.exc_info()[1].__str__())
        return imagefilename


    def getInfoFromLotsData(self, htmlList, imagepath, downloadimages):
        baseUrl = "https://www.tiroche.co.il"
        info = []
        endSpacePattern = re.compile("\s+$", re.DOTALL)
        beginspacePattern = re.compile("^\s+")
        emptyspacePattern = re.compile("^\s*$")
        brPattern = re.compile("<br\s*\/?>", re.IGNORECASE)
        trailingdotPattern = re.compile("\s*\.\s*$")
        measureunitPattern = re.compile("([a-zA-Z]{2})")
        lotnoPattern = re.compile("Lot\s*\:\s+(\d+)")
        mediumPattern = re.compile("(gold)|(silver)|(brass)|(bronze)|(wood)|(porcelain)|(stone)|(marble)|(metal)|(steel)|(iron)|(glass)|(plexiglas)|(chromogenic)|(paper)|(canvas)|(masonite)|(newsprint)|(silkscreen)|(parchment)|(linen)|(inkjet)|(ink\s+jet)|(pigment)|(\stin\s)|(photogravure)|(^oil\s+)|(\s+panel\s+)|(terracotta)|(ivory)|(\s+oak\s+)|(^oak\s+)|(\s+oak$)|(alabaster)|(polycarbonate\s+honeycomb)|(c\-print)|(acrylic)|(burlap)|(colou?r\s+photograph)|(gouache)|(terra\s+cotta)|(terracotta)|(on\s+panel)|(lithograph)|(on\s+board)|(sculpture)|(ceramic)|(photographic\s+printing)|(poster)|(dye\-transfer)|(cibachrome)", re.DOTALL|re.IGNORECASE)
        sizePattern = re.compile("([\d\.X\s]+\s*cm)", re.IGNORECASE|re.DOTALL)
        signedPattern = re.compile("(signed.*)",re.IGNORECASE)
        lotctr = 1
        for htmldiv in htmlList:
            data = {}
            data['auction_num'] = self.saleno
            detailUrl = ""
            lotno = ""
            data['price_estimate_min'] = ""
            data['price_estimate_max'] = ""
            data['artist_name'] = ""
            data['artwork_name'] = ""
            data['lot_num'] = ""
            data['lot_origin_url'] = ""
            htmlContent = htmldiv.renderContents().decode('utf-8')
            s = BeautifulSoup(htmlContent, features="html.parser")
            lotnodiv = s.find("div", {'class' : 'lot-item__head'})
            if not lotnodiv:
                continue
            lotnocontents = lotnodiv.renderContents().decode('utf-8')
            lotnocontents = lotnocontents.replace("\n", "").replace("\r", "")
            lotnocontents = self.__class__.htmltagPattern.sub("", lotnocontents)
            lps = re.search(lotnoPattern, lotnocontents)
            if lps:
                data['lot_num'] = lps.groups()[0]
                lotno = data['lot_num']
            else:
                continue # If we couldn't extract the lot number, there is no use going any further.
            anchortags = s.find_all("a")
            if anchortags.__len__() > 0:
                anchortag = anchortags[0]
                detailUrl = anchortag['href']
                data['lot_origin_url'] = detailUrl
            artistanchortag = s.find("a", {'class' : 'title'})
            if artistanchortag:
                data['artist_name'] = artistanchortag.renderContents().decode('utf-8')
            titledivtag = s.find("div", {'class' : 'desc'})
            if titledivtag:
                 artworkdetails = titledivtag.renderContents().decode('utf-8')
                 detailparts = artworkdetails.split(",")
                 data['artwork_name'] = detailparts[0]
                 for detpart in detailparts:
                     mps = re.search(mediumPattern, detpart)
                     zps = re.search(sizePattern, detpart)
                     sps = re.search(signedPattern, detpart)
                     if mps:
                         data['artwork_materials'] = mps.groups()[0]
                     if zps:
                         data['artwork_size_notes'] = zps.groups()[0]
                         dimensions = data['artwork_size_notes']
                         dimparts = dimensions.split("X")
                         data['artwork_measurements_height'] = dimparts[0]
                         if dimparts.__len__() > 1:
                             data['artwork_measurements_width'] = dimparts[1]
                             mups = re.search(measureunitPattern, data['artwork_measurements_width'])
                             if mups:
                                 data['auction_measureunit'] = mups.groups()[0]
                                 data['artwork_measurements_width'] = measureunitPattern.sub("", data['artwork_measurements_width'])
                                 data['artwork_measurements_width'] = trailingdotPattern.sub("", data['artwork_measurements_width'])
                         if dimparts.__len__() > 2:
                             data['artwork_measurements_depth'] = dimparts[2]
                             mups = re.search(measureunitPattern, data['artwork_measurements_depth'])
                             if mups:
                                 data['auction_measureunit'] = mups.groups()[0]
                                 data['artwork_measurements_depth'] = measureunitPattern.sub("", data['artwork_measurements_depth'])
                                 data['artwork_measurements_depth'] = trailingdotPattern.sub("", data['artwork_measurements_depth'])
                     if sps:
                         data['artwork_markings'] = sps.groups()[0]
            yearspantag = s.find("span", {'class' : 'title_and_year_year'})
            if yearspantag:
                data['artwork_start_year'] = yearspantag.renderContents().decode('utf-8')
            priceptag = s.find("p", {'class' : 'bp-price sold-price'})
            if priceptag:
                price = priceptag.renderContents().decode('utf-8')
                price = price.replace("\n", "").replace("\r", "")
                data['price_sold'] = price
            #print(data['lot_num'] + " ## " + data['artist_name'] + " ## " + data['artwork_name'] + " ## " + data['price_sold'])
            print("Getting '%s'..."%data['lot_origin_url'])
            if detailUrl == "":
                break
            detailsPageContent = self.getDetailsPage(detailUrl)
            detailData = self.parseDetailPage(detailsPageContent, lotno, imagepath, data['artist_name'], data['artwork_name'], downloadimages)
            for k in detailData.keys():
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
            if 'price_sold' not in data.keys():
                data['price_sold'] = ""
            data['auction_name'] = self.auctiontitle
            data['auction_start_date'] = self.auctiondate
            data['auction_location'] = "London"
            lotctr += 1
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
    pageurl = "http://216.137.189.57:8080/scrapers/finish/?scrapername=Tiroche&auctionnumber=%s&auctionurl=%s&scrapertype=2"%(auctionno, urllib.parse.quote(auctionurl))
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
    auctionurl = auctionurl
    tbot = TirocheBot(auctionurl, auctionnumber)
    fp = open(csvpath, "w")
    fieldnames = ['auction_house_name', 'auction_location', 'auction_num', 'auction_start_date', 'auction_end_date', 'auction_name', 'lot_num', 'sublot_num', 'price_kind', 'price_estimate_min', 'price_estimate_max', 'price_sold', 'artist_name', 'artist_birth', 'artist_death', 'artist_nationality', 'artwork_name', 'artwork_year_identifier', 'artwork_start_year', 'artwork_end_year', 'artwork_materials', 'artwork_category', 'artwork_markings', 'artwork_edition', 'artwork_description', 'artwork_measurements_height', 'artwork_measurements_width', 'artwork_measurements_depth', 'artwork_size_notes', 'auction_measureunit', 'artwork_condition_in', 'artwork_provenance', 'artwork_exhibited', 'artwork_literature', 'artwork_images1', 'artwork_images2', 'artwork_images3', 'artwork_images4', 'artwork_images5', 'image1_name', 'image2_name', 'image3_name', 'image4_name', 'image5_name', 'lot_origin_url']
    fieldsstr = ",".join(fieldnames)
    fp.write(fieldsstr + "\n")
    pagectr = 1
    soup = BeautifulSoup(tbot.currentPageContent, features="html.parser")
    while True:
        lotsdata = tbot.getLotsFromPage()
        info = tbot.getInfoFromLotsData(lotsdata, imagepath, downloadimages)
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
        nextpageanchor = soup.find("a", {'class' : 'next page-numbers'})
        if nextpageanchor is not None:
            nextpageUrl = nextpageanchor['href']
            tbot.pageRequest = urllib.request.Request(nextpageUrl, headers=tbot.httpHeaders)
            try:
                tbot.pageResponse = tbot.opener.open(tbot.pageRequest)
            except:
                print("Couldn't find the page %s"%str(pagectr))
                break
            tbot.currentPageContent = tbot.__class__._decodeGzippedContent(tbot.getPageContent())
            soup = BeautifulSoup(tbot.currentPageContent, features="html.parser")
        else:
            break
    fp.close()
    updatestatus(auctionnumber, auctionurl)

# Example: python tiroche.py "https://omertiroche.com/exhibitions/28-dali-sketchbooks-from-the-1930s/works/" 28 /home/supmit/work/art2/tiroche_28.csv /home/supmit/work/art2/images/tiroche/28 0 0
# supmit


