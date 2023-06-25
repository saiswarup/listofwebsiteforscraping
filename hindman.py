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
from datetime import date
import unidecode

partialUrlPattern = re.compile("^/\w+")

def decodeHtmlEntities(content):
    entitiesDict = {'&nbsp;' : ' ', '&quot;' : '"', '&lt;' : '<', '&gt;' : '>', '&amp;' : '&', '&apos;' : "'", '&#160;' : ' ', '&#60;' : '<', '&#62;' : '>', '&#38;' : '&', '&#34;' : '"', '&#39;' : "'"}
    for entity in entitiesDict.keys():
        content = content.replace(entity, entitiesDict[entity])
    return content


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


class HindmanBot(object):
    
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
        self.requestUrl = auctionurl + "?page=1&per=500"
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
        return decoded_content

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
        return cookies

    _getCookieFromResponse = classmethod(_getCookieFromResponse)


    def getPageContent(self):
        return self.pageResponse.read()


    def formatDate(cls, datestr):
        mondict = {'Jan' : '01', 'Feb' : '02', 'Mar' : '03', 'Apr' : '04', 'May' : '05', 'Jun' : '06', 'Jul' : '07', 'Aug' : '08', 'Sep' : '09', 'Oct' : '10', 'Nov' : '11', 'Dec' : '12' }
        mondict3 = {'jan.' : '01', 'fév.' : '02', 'mar.' : '03', 'avr.' : '04', 'mai.' : '05', 'jui.' : '06', 'jul.' : '07', 'aoû.' : '08', 'sep.' : '09', 'oct.' : '10', 'nov.' : '11', 'déc.' : '12' }
        mondict4 = {'Janvier' : '01', 'Février' : '02', 'Mars' : '03', 'Avril' : '04', 'Mai' : '05', 'Juin' : '06', 'Juillet' : '07', 'Août' : '08', 'Septembre' : '09', 'Octobre' : '10', 'Novembre' : '11', 'Décembre' : '12'}
        datestrcomponents = datestr.split(" ")
        if not datestr:
            return ""
        if datestrcomponents.__len__() < 3:
            return ""
        dd = datestrcomponents[1]
        mon = datestrcomponents[0].capitalize()
        year = datestrcomponents[2]
        monstr = mon
        if datestrcomponents[0] in mondict.keys():
            mm = mondict[datestrcomponents[0]]
        else:
            try:
                mm = mondict3[datestrcomponents[0]]
            except:
                mm = mondict4[datestrcomponents[0]]
        retdate = dd + "-" + monstr + "-" + year[2:]
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
        title = ""
        allh1tags = soup.find_all("h1", {'class' : 'c-AuctionHeader__title'})
        if allh1tags.__len__() > 0:
            title = allh1tags[0].renderContents().decode('utf-8')
            titleparts = title.split(":")
            if titleparts.__len__() > 0:
                self.auctiontitle = titleparts[0]
        if not title or title == "":
            titledivtags = soup.find_all("div", {'class' : '_c-AuctionHeaderUpcoming__title'})
            if titledivtags.__len__() > 0:
                title = titledivtags[0].renderContents().decode('utf-8')
                title = title.replace("\n", "").replace("\r", "")
                title = self.__class__.htmltagPattern.sub("", title)
                self.auctiontitle = title
        allh3romantags = soup.find_all("h3", {'class' : 'romain_headline_regular'})
        if allh3romantags.__len__() > 0:
            h3content = allh3romantags[0].renderContents().decode('utf-8')
            datePattern = re.compile("(\w+\s+\d{1,2}\,\s+\d{4})")
            dps = re.search(datePattern, h3content)
            if dps:
                self.auctiondate = dps.groups()[0]
        datedivtags = soup.find_all("div", {'class' : 'auction_days'})
        if datedivtags.__len__() > 0:
            auctiondate = datedivtags[0].renderContents().decode('utf-8')
            auctiondate = auctiondate.replace("\n", "").replace("\r", "")
            auctiondate = self.__class__.htmltagPattern.sub("", auctiondate)
            datePattern = re.compile("(\w{3}\s+\d{1,2})")
            dps = re.search(datePattern, auctiondate)
            if dps:
                self.auctiondate = dps.groups()[0]
                todays_date = date.today()
                curryear = str(todays_date.year)
                self.auctiondate += ", " + curryear
        lotsPattern = re.compile("lots:(\[[^\]]+\])", re.DOTALL)
        lotsblock = {}
        lps = re.search(lotsPattern, pageContent)
        if lps:
            lpsg = lps.groups()
            lotcontent = lpsg[0]
            lot_numbers = []
            """
            lotnumberPattern = re.compile("lot_number\:([^\,]+)\,", re.DOTALL)
            lnmatches = re.findall(lotnumberPattern, lotcontent)
            nonnumericPattern = re.compile("^[^\d]*$")
            lastlotno = 0
            lastlnmatch = ""
            lotnodict = {}
            for lnmatch in lnmatches:
                lnmatch = lnmatch.replace('"', "").replace("'", "")
                #print(lnmatch)
                if re.search(nonnumericPattern, lnmatch):
                    if lastlnmatch == lnmatch:
                        continue
                    lastlnmatch = lnmatch
                    lnmatch = lastlotno + 1
                    #lnmatch = lastlotno
                lastlotno = int(lnmatch)
                #lastlotno = lnmatch
                if str(lnmatch) in lotnodict.keys():
                    lot_numbers.pop()
                else:
                    lotnodict[str(lnmatch)] = 1
                lot_numbers.append(lnmatch)
                #print("lnmatch = %s, lotno = %s"%(lnmatch, lot_numbers[-1]))
            """
            lotnumberspanPattern = re.compile("c\-GridItem__lot\-number")
            lotnospantags = soup.find_all("div", {'class' : lotnumberspanPattern})
            lotnumberPattern = re.compile("Lot\s+(\d+)")
            lotnumberPattern2 = re.compile("\s*(\d+)")
            for lotnospan in lotnospantags:
                lotnocontents = lotnospan.renderContents().decode('utf-8')
                #print(lotnocontents)
                lps = re.search(lotnumberPattern, lotnocontents)
                lps2 = re.search(lotnumberPattern2, lotnocontents)
                if lps:
                    lotno = lps.groups()[0]
                    lot_numbers.append(lotno)
                elif lps2:
                    lotno = lps2.groups()[0]
                    lot_numbers.append(lotno)
            #print(lot_numbers.__len__())
            slugPattern = re.compile("\,slug\:\"([^\"]+)\"\,", re.DOTALL)
            slugmatches = re.findall(slugPattern, lotcontent)
            slugs = []
            for slugmatch in slugmatches:
                slugs.append(slugmatch)
            titlePattern = re.compile("\,title\:\"([^\"]+)\"")
            titlematches = re.findall(titlePattern, lotcontent)
            titles = []
            for titlematch in titlematches:
                titles.append(titlematch)
            lotblocks = {'titles' : titles, 'slugs' : slugs, 'lotnumbers' : lot_numbers}
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


    def parseDetailPage(self, detailsPage, lotno, imagepath, downloadimages):
        baseUrl = "https://hindmanauctions.com"
        detailData = {}
        nonnumericPattern = re.compile("([^\d\/\.\s]+)")
        matcatdict_en = {}
        matcatdict_fr = {}
        detailData['price_sold'] = ""
        conditionPattern = re.compile("condition:\"([^\"]+)\"")
        beginspacePattern = re.compile("^\s+")
        enddecimalPattern = re.compile("\.\s*")
        with open("/Users/saiswarupsahu/freelanceprojectchetan/docs/fineart_materials.csv", newline='') as mapfile:
        #with open("docs/fineart_materials.csv", newline='') as mapfile:
            mapreader = csv.reader(mapfile, delimiter=",", quotechar='"')
            for maprow in mapreader:
                matcatdict_en[maprow[1]] = maprow[3]
                matcatdict_fr[maprow[2]] = maprow[3]
        mapfile.close()
        soup = BeautifulSoup(detailsPage, features="html.parser")
        saleinfodivtags = soup.find_all("div", {'class' : 'sale_info'})
        if saleinfodivtags.__len__() > 0:
            saleinfodivcontent = saleinfodivtags[0].renderContents().decode('utf-8')
            lotnoPattern = re.compile("Lot\s+(\d+)", re.DOTALL)
            lps = re.search(lotnoPattern, saleinfodivcontent)
            if lps:
                lotno = lps.groups()[0]
                detailData['lot_num'] = lotno
        cps = re.search(conditionPattern, detailsPage)
        if cps:
            condition = cps.groups()[0]
            condition = condition.replace("\u003C", "<").replace("\u003E", ">")
            condition = self.__class__.htmltagPattern.sub("", condition)
            #detailData['artwork_condition_in'] = condition
        lotdetaildivtags = soup.find_all("div", {'class' : 'LotItem__lotDescription'})
        lotdescdivtag = None
        if lotdetaildivtags.__len__() > 0:
            lotdescnextdivtag = lotdetaildivtags[0].findNext("div", {'class' : 'creation_time'})
            if lotdescnextdivtag is not None:
                lotdescdivtag = lotdescnextdivtag.parent
                lotdetails = lotdescdivtag.text
                lotdetails = lotdetails.replace("\n", "").replace("\r", "")
                lotdetails = self.__class__.htmltagPattern.sub("", lotdetails)
            else:
                lotdetails = lotdetaildivtags[0].renderContents().decode('utf-8')
                lotdetails = lotdetails.replace("\n", "").replace("\r", "")
                lotdetails = self.__class__.htmltagPattern.sub("", lotdetails)
            detailData['artwork_description'] = lotdetails
            detailData['artwork_description'] = detailData['artwork_description'].strip()
            detailData['artwork_description'] = self.__class__.htmltagPattern.sub("", detailData['artwork_description'])
            detailData['artwork_description'] = detailData['artwork_description'].replace("\n", " ")
            detailData['artwork_description'] = detailData['artwork_description'].replace("\r", " ")
            detailData['artwork_description'] = detailData['artwork_description'].replace('"', "'")
            detailData['artwork_description'] = detailData['artwork_description'].replace("Provenance", "<br><strong>Provenance</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("Literature", "<br><strong>Literature</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("Exhibited", "<br><strong>Exhibited</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("Condition Report", "<br><strong>Condition Report</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("Notes:", "<br><strong>Notes:</strong><br>")
        if 'artwork_description' in detailData.keys():
            detailData['artwork_description'] = "<strong><br>Description<br></strong>" + detailData['artwork_description']
        if lotdescdivtag is not None:
            artistbtags = lotdescdivtag.findChildren("b")
            if artistbtags.__len__() > 0:
                artistinfo = artistbtags[0].renderContents().decode('utf-8')
                artistinfo = artistinfo.replace("\n", "").replace("\r", "")
                artistinfo = self.__class__.htmltagPattern.sub("", artistinfo)
                detailData['artist_name'] = artistinfo
        artistbirthdeathdivtags = soup.find_all("div", {'class' : 'creation_time'})
        if artistbirthdeathdivtags.__len__() > 0:
            artistbirthdeathdiv = artistbirthdeathdivtags[0]
            artistbirthdeathcontent = artistbirthdeathdiv.renderContents().decode('utf-8')
            birthdeathPattern = re.compile("\s+([\d]{4})\-?(\d{0,4})", re.DOTALL)
            nationalityPattern = re.compile("\(([\w\s\/]+),?\s+[\d]{4}\-?\d{0,4}\)", re.DOTALL)
            nationalityPattern2 = re.compile("\(([\w\s\/]+),?\s+b\.\s+[\d]{4}\)", re.DOTALL)
            bdps = re.search(birthdeathPattern, artistbirthdeathcontent)
            if bdps:
                bdpsg = bdps.groups()
                birthdate = bdpsg[0]
                deathdate = bdpsg[1]
                detailData['artist_birth'] = birthdate
                detailData['artist_death'] = deathdate
            nps = re.search(nationalityPattern, artistbirthdeathcontent)
            if nps:
                detailData['artist_nationality'] = nps.groups()[0]
            nps2 = re.search(nationalityPattern2, artistbirthdeathcontent)
            if 'artist_nationality' not in detailData.keys() and nps2:
                detailData['artist_nationality'] = nps2.groups()[0]
        mediumdivtags = soup.find_all("div", {'class' : 'mediums'})
        if mediumdivtags.__len__() > 0:
            mediumdiv = mediumdivtags[0]
            mediumcontent = mediumdiv.renderContents().decode('utf-8')
            detailData['artwork_materials'] = mediumcontent
        detailData['auction_measureunit'] = ""
        sizedivtags = soup.find_all("div", {'class' : 'dimensions'})
        if sizedivtags.__len__() > 0:
            sizecontent = sizedivtags[0].renderContents().decode('utf-8')
            detailData['artwork_size_notes'] = sizecontent
            sizeparts = sizecontent.split("x")
            if sizeparts.__len__() > 2:
                detailData['artwork_measurements_height'] = sizeparts[0]
                sizeparts[1] = nonnumericPattern.sub("", sizeparts[1])
                detailData['artwork_measurements_width'] = sizeparts[1]
                zps = re.search(nonnumericPattern, sizeparts[2])
                if zps:
                    detailData['auction_measureunit'] = zps.groups()[0]
                sizeparts[2] = nonnumericPattern.sub("", sizeparts[2])
                detailData['artwork_measurements_depth'] = sizeparts[2]
            elif sizeparts.__len__() > 1:
                detailData['artwork_measurements_height'] = sizeparts[0]
                zps = re.search(nonnumericPattern, sizeparts[1])
                if zps:
                    detailData['auction_measureunit'] = zps.groups()[0]
                sizeparts[1] = nonnumericPattern.sub("", sizeparts[1])
                detailData['artwork_measurements_width'] = sizeparts[1]
            elif sizeparts.__len__() > 0:
                zps = re.search(nonnumericPattern, sizeparts[0])
                if zps:
                    detailData['auction_measureunit'] = zps.groups()[0]
                detailData['artwork_measurements_height'] = sizeparts[0]
            if 'artwork_measurements_width' in detailData.keys():
                detailData['artwork_measurements_width'] = beginspacePattern.sub("", detailData['artwork_measurements_width'])
                detailData['artwork_measurements_width'] = enddecimalPattern.sub("", detailData['artwork_measurements_width'])
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
        provenancedivtags = soup.find_all("div", {'class' : 'f-body-16-14 u-block mb-12'})
        if provenancedivtags.__len__() > 0:
            provenancetext = provenancedivtags[0].renderContents().decode('utf-8')
            provenancetext = provenancetext.replace("\n", "").replace("\r", "")
            brPattern = re.compile("<br\s*\/?><br\s*\/?>")
            provenanceparts = re.split(brPattern, provenancetext)
            provenancePattern = re.compile("provenance", re.IGNORECASE|re.DOTALL)
            exhibitionPattern = re.compile("exhibited", re.IGNORECASE|re.DOTALL)
            for provenancepart in provenanceparts:
                provenancepart = self.__class__.htmltagPattern.sub("", provenancepart)
                if re.search(provenancePattern, provenancepart):
                    provenancepart = provenancepart.replace("<!--block-->", "")
                    provenancepart = provenancepart.replace("Provenance:", "")
                    detailData['artwork_provenance'] = provenancepart
                if re.search(exhibitionPattern, provenancepart):
                    provenancepart = provenancepart.replace("<!--block-->", "")
                    provenancepart = provenancepart.replace("Exhibited:", "")
                    detailData['artwork_exhibited'] = provenancepart
        titledivtags = soup.find_all("div", {'class' : 'title'})
        if titledivtags.__len__() > 0:
            titlecontents = titledivtags[0].renderContents().decode('utf-8')
            titlecontents = titlecontents.replace("\n", "").replace("\r", "")
            titlecontents = self.__class__.htmltagPattern.sub("", titlecontents)
            detailData['artwork_name'] = titlecontents
            detailData['artwork_name'] = detailData['artwork_name'].replace('"', "'")
            yearPattern = re.compile("(\d{4})")
            yps = re.search(yearPattern, titlecontents)
            if yps:
                detailData['artwork_start_year'] = yps.groups()[0]
        pricingulPattern = re.compile("c-LotPricing")
        pricingdivPattern = re.compile("LotItem__priceAmount")
        pricingultags = soup.find_all("ul", {'class' : pricingulPattern})
        pricingdivtags = soup.find_all("div", {'class' : pricingdivPattern})
        if pricingultags.__len__() > 0:
            pricingcontent = pricingultags[0].renderContents().decode('utf-8')
            pricingcontent = pricingcontent.replace("\n", "").replace("\r", "")
            pricingcontent = self.__class__.htmltagPattern.sub("", pricingcontent)
            pricingPattern = re.compile("\$([\d,\.]+)\s*\-\s*\$?([\d,\.]+)", re.DOTALL)
            pps = re.search(pricingPattern, pricingcontent)
            if pps:
                ppsg = pps.groups()
                low = ppsg[0]
                high = ppsg[1]
                detailData['price_estimate_min'] = low
                detailData['price_estimate_max'] = high
            soldfordiv = pricingultags[0].findNext("div")
            if soldfordiv:
                soldforcontent = soldfordiv.renderContents().decode('utf-8')
                soldforPattern = re.compile("Sold\s+for\s+\$([\d,\.]+)", re.DOTALL|re.IGNORECASE)
                sps = re.search(soldforPattern, soldforcontent)
                if sps:
                    spsg = sps.groups()
                    detailData['price_sold'] = spsg[0]
                    detailData['price_sold'] = detailData['price_sold'].replace(",", "")
        elif pricingdivtags.__len__() > 0:
            pricingcontent = pricingdivtags[0].renderContents().decode('utf-8')
            pricingcontent = pricingcontent.replace("\n", "").replace("\r", "")
            pricingcontent = self.__class__.htmltagPattern.sub("", pricingcontent)
            pricingPattern = re.compile("\$([\d,\.]+)\s*\-\s*\$?([\d,\.]+)", re.DOTALL)
            pps = re.search(pricingPattern, pricingcontent)
            if pps:
                ppsg = pps.groups()
                low = ppsg[0]
                high = ppsg[1]
                detailData['price_estimate_min'] = low
                detailData['price_estimate_max'] = high
            soldforh1 = pricingdivtags[0].findNext("h1")
            if soldforh1:
                soldforcontent = soldforh1.renderContents().decode('utf-8')
                soldforPattern = re.compile("Sold\s+for\s+\$([\d,\.]+)", re.DOTALL|re.IGNORECASE)
                sps = re.search(soldforPattern, soldforcontent)
                if sps:
                    spsg = sps.groups()
                    detailData['price_sold'] = spsg[0]
                    detailData['price_sold'] = detailData['price_sold'].replace(",", "")
        else:
            pass
        withdrawnPattern = re.compile("withdrawn", re.IGNORECASE|re.DOTALL)
        detailData['price_kind'] = "unknown"
        if ('price_sold' in detailData.keys() and re.search(withdrawnPattern, detailData['price_sold'])) or ('price_estimate_max' in detailData.keys() and re.search(withdrawnPattern, detailData['price_estimate_max'])):
            detailData['price_kind'] = "withdrawn"
        elif 'price_sold' in detailData.keys() and detailData['price_sold'] != "":
            detailData['price_kind'] = "price realized"
        elif 'price_estimate_max' in detailData.keys() and detailData['price_estimate_max'] != "":
            detailData['price_kind'] = "estimate"
        else:
            pass
        imagesdivtags = soup.find_all("div", {'class' : 'c-LotImageCarousel__thumbnails'})
        defaultimgeurl = ""
        artistname = ""
        if 'artist_name' in detailData.keys():
            artistname = detailData['artist_name']
        auction_number = self.saleno
        lot_number = lotno
        if imagesdivtags.__len__() > 0:
            allimgtags = imagesdivtags[0].find_all("img")
            altimages = []
            if allimgtags.__len__() > 0:
                defaultimgeurl = allimgtags[0]['src']
            defaultimgeurl = defaultimgeurl.strip()
            for altimg in allimgtags[1:]:
                altimgurl = altimg['src']
                altimages.append(altimgurl)
            imagename1 = self.getImagenameFromUrl(defaultimgeurl)
            imagename1 = str(imagename1)
            imagename1 = imagename1.replace("b'", "").replace("'", "")
            auctiontitle = self.auctiontitle.replace(" ", "_")
            processedAuctionTitle = auctiontitle.replace(" ", "_")
            processedArtistName = artistname.replace(" ", "_")
            processedArtworkName = detailData['artwork_name'].replace(" ", "_")
            sublot_number = ""
            newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + auction_number + "__" + lot_number + "__" + sublot_number
            encryptedFilename = self.encryptFilename(newname1)
            imagepathparts = defaultimgeurl.split("/")
            defimageurl = "/".join(imagepathparts[:-2])
            encryptedFilename = str(encryptedFilename).replace("b'", "")
            encryptedFilename = str(encryptedFilename).replace("'", "")
            detailData['image1_name'] = str(encryptedFilename) + ".jpg"
            detailData['artwork_images1'] = defaultimgeurl
            self.getImage(detailData['artwork_images1'], imagepath, downloadimages)
            """
            if downloadimages == "1":
                encryptedFilename = str(encryptedFilename) + "-a.jpg"
                self.renameImageFile(imagepath, imagename1, encryptedFilename)
            """
            imgctr = 2
            if altimages.__len__() > 0:
                altimage2 = altimages[0]
                altimage2parts = altimage2.split("/")
                altimageurl = "/".join(altimage2parts[:-2])
                processedArtistName = artistname.replace(" ", "_")
                processedArtistName = unidecode.unidecode(processedArtistName)
                processedArtworkName = detailData['artwork_name'].replace(" ", "_")
                sublot_number = ""
                #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + auction_number + "__" + lot_number + "__" + sublot_number
                newname1 = auction_number + "__" + processedArtistName + "__" + str(lot_number) + "_b"
                #encryptedFilename = self.encryptFilename(newname1)
                encryptedFilename = newname1
                detailData['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
                detailData['artwork_images' + str(imgctr)] = altimage2
                self.getImage(detailData['artwork_images' + str(imgctr)], imagepath, downloadimages)
                """
                if downloadimages == "1":
                    encryptedFilename = str(encryptedFilename) + "-b.jpg"
                    self.renameImageFile(imagepath, imagename1, encryptedFilename)
                """
                imgctr += 1
            if altimages.__len__() > 1:
                altimage3 = altimages[1]
                altimage3parts = altimage3.split("/")
                altimageurl = "/".join(altimage3parts[:-2])
                detailData['image' + str(imgctr) + '_name'] = self.getImagenameFromUrl(altimage3)
                processedArtistName = artistname.replace(" ", "_")
                processedArtistName = unidecode.unidecode(processedArtistName)
                processedArtworkName = detailData['artwork_name'].replace(" ", "_")
                sublot_number = ""
                #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + auction_number + "__" + lot_number + "__" + sublot_number
                newname1 = auction_number + "__" + processedArtistName + "__" + str(lot_number) + "_c"
                #encryptedFilename = self.encryptFilename(newname1)
                encryptedFilename = newname1
                detailData['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
                detailData['artwork_images' + str(imgctr)] = altimage3
                self.getImage(detailData['artwork_images' + str(imgctr)], imagepath, downloadimages)
                """
                if downloadimages == "1":
                    encryptedFilename = str(encryptedFilename) + "-c.jpg"
                    self.renameImageFile(imagepath, imagename1, encryptedFilename)
                """
                imgctr += 1
            if altimages.__len__() > 2:
                altimage4 = altimages[2]
                altimage4parts = altimage4.split("/")
                altimageurl = "/".join(altimage4parts[:-2])
                detailData['image' + str(imgctr) + '_name'] = self.getImagenameFromUrl(altimage4)
                processedArtistName = artistname.replace(" ", "_")
                processedArtistName = unidecode.unidecode(processedArtistName)
                processedArtworkName = detailData['artwork_name'].replace(" ", "_")
                sublot_number = ""
                #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + auction_number + "__" + lot_number + "__" + sublot_number
                newname1 = auction_number + "__" + processedArtistName + "__" + str(lot_number) + "_d"
                #encryptedFilename = self.encryptFilename(newname1)
                encryptedFilename = newname1
                detailData['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
                detailData['artwork_images' + str(imgctr)] = altimage4
                self.getImage(detailData['artwork_images' + str(imgctr)], imagepath, downloadimages)
                """
                if downloadimages == "1":
                    encryptedFilename = str(encryptedFilename) + "-d.jpg"
                    self.renameImageFile(imagepath, imagename1, encryptedFilename)
                """
                imgctr += 1
            if altimages.__len__() > 3:
                altimage5 = altimages[3]
                altimage5parts = altimage5.split("/")
                altimageurl = "/".join(altimage5parts[:-2])
                detailData['image' + str(imgctr) + '_name'] = self.getImagenameFromUrl(altimage5)
                processedArtistName = artistname.replace(" ", "_")
                processedArtistName = unidecode.unidecode(processedArtistName)
                processedArtworkName = detailData['artwork_name'].replace(" ", "_")
                sublot_number = ""
                #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + auction_number + "__" + lot_number + "__" + sublot_number
                newname1 = auction_number + "__" + processedArtistName + "__" + str(lot_number) + "_e"
                #encryptedFilename = self.encryptFilename(newname1)
                encryptedFilename = newname1
                detailData['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
                detailData['artwork_images' + str(imgctr)] = altimage5
                self.getImage(detailData['artwork_images' + str(imgctr)], imagepath, downloadimages)
                """
                if downloadimages == "1":
                    encryptedFilename = str(encryptedFilename) + "-e.jpg"
                    self.renameImageFile(imagepath, imagename1, encryptedFilename)
                """
                imgctr += 1
        if defaultimgeurl == "" or not defaultimgeurl:
            imageurlPattern = re.compile('large\:"([^"]+)"', re.DOTALL)
            ips = re.search(imageurlPattern, detailsPage)
            if ips:
                defaultimgeurl = ips.groups()[0]
                defaultimgeurl = defaultimgeurl.replace("\\u002F", "/")
            imagename1 = self.getImagenameFromUrl(defaultimgeurl)
            imagename1 = str(imagename1)
            imagename1 = imagename1.replace("b'", "").replace("'", "")
            auctiontitle = self.auctiontitle.replace(" ", "_")
            processedAuctionTitle = auctiontitle.replace(" ", "_")
            processedArtistName = artistname.replace(" ", "_")
            processedArtistName = unidecode.unidecode(processedArtistName)
            processedArtworkName = detailData['artwork_name'].replace(" ", "_")
            sublot_number = ""
            #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + auction_number + "__" + lot_number + "__" + sublot_number
            newname1 = auction_number + "__" + processedArtistName + "__" + str(lot_number) + "_a"
            #encryptedFilename = self.encryptFilename(newname1)
            encryptedFilename = newname1
            imagepathparts = defaultimgeurl.split("/")
            defimageurl = "/".join(imagepathparts[:-2])
            encryptedFilename = str(encryptedFilename).replace("b'", "")
            encryptedFilename = str(encryptedFilename).replace("'", "")
            detailData['image1_name'] = str(encryptedFilename) + ".jpg"
            detailData['artwork_images1'] = defaultimgeurl
            self.getImage(detailData['artwork_images1'], imagepath, downloadimages)
            """
            if downloadimages == "1":
                encryptedFilename = str(encryptedFilename) + "-a.jpg"
                self.renameImageFile(imagepath, imagename1, encryptedFilename)
            """
        stickydivtags = soup.find_all("div", {'class' : 'c-LotDetail__sticky'})
        if stickydivtags.__len__() > 0:
            stickydivcontent = stickydivtags[0].renderContents().decode('utf-8')
            stickydivparts = stickydivcontent.split("\n")
            signedPattern = re.compile("signed", re.IGNORECASE)
            for stickydivpart in stickydivparts:
                gps = re.search(signedPattern, stickydivpart)
                if gps and 'artwork_markings' not in detailData.keys():
                    stickydivpart = self.__class__.htmltagPattern.sub("", stickydivpart)
                    stickydivpart = stickydivpart.replace("\r", "")
                    detailData['artwork_markings'] = stickydivpart
        auctiondateparts = self.auctiondate.split(" ")
        detailData['auction_start_date'] = self.__class__.formatDate(self.auctiondate)
        detailData['auction_house_name'] = "Hindman"
        detailData['auction_num'] = self.saleno
        detailData['auction_location'] = "Chicago"
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


    def getInfoFromLotsData(self, lotsdict, imagepath, downloadimages):
        baseUrl = "https://hindmanauctions.com"
        info = []
        endSpacePattern = re.compile("\s+$", re.DOTALL)
        slugs = lotsdict['slugs']
        titles = lotsdict['titles']
        lotnumbers = lotsdict['lotnumbers']
        lotctr = 0
        for lotctr in range(0, slugs.__len__()):
            data = {}
            detailUrl = baseUrl + "/items/" +  slugs[lotctr]
            data['lot_origin_url'] = detailUrl
            lotno = ""
            if lotctr < titles.__len__():
                data['artwork_name'] = titles[lotctr]
                data['artwork_name'] = data['artwork_name'].replace('"', "'")
            if lotctr < lotnumbers.__len__():
                lotno = lotnumbers[lotctr]
            else:
                break
            lotno = str(lotno).replace('"', "")
            data['lot_num'] = lotno
            print("Getting '%s'..."%detailUrl)
            detailsPageContent = self.getDetailsPage(detailUrl)
            detailData = self.parseDetailPage(detailsPageContent, lotno, imagepath, downloadimages)
            for k in detailData.keys():
                data[k] = detailData[k]
            data['auction_name'] = self.auctiontitle
            if 'price_estimate_min' in data.keys():
                data['price_estimate_min'] = data['price_estimate_min'].replace(",", "").replace(" ", "")
            if 'price_estimate_max' in data.keys():
                data['price_estimate_max'] = data['price_estimate_max'].replace(",", "").replace(" ", "")
            if 'price_sold' in data.keys():
                data['price_sold'] = data['price_sold'].replace(",", "").replace(" ", "")
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
    pageurl = "http://216.137.189.57:8080/scrapers/finish/?scrapername=Hindman&auctionnumber=%s&auctionurl=%s&scrapertype=2"%(auctionno, urllib.parse.quote(auctionurl))
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
    hindman = HindmanBot(auctionurl, auctionnumber)
    fp = open(csvpath, "w")
    fieldnames = ['auction_house_name', 'auction_location', 'auction_num', 'auction_start_date', 'auction_end_date', 'auction_name', 'lot_num', 'sublot_num', 'price_kind', 'price_estimate_min', 'price_estimate_max', 'price_sold', 'artist_name', 'artist_birth', 'artist_death', 'artist_nationality', 'artwork_name', 'artwork_year_identifier', 'artwork_start_year', 'artwork_end_year', 'artwork_materials', 'artwork_category', 'artwork_markings', 'artwork_edition', 'artwork_description', 'artwork_measurements_height', 'artwork_measurements_width', 'artwork_measurements_depth', 'artwork_size_notes', 'auction_measureunit', 'artwork_condition_in', 'artwork_provenance', 'artwork_exhibited', 'artwork_literature', 'artwork_images1', 'artwork_images2', 'artwork_images3', 'artwork_images4', 'artwork_images5', 'image1_name', 'image2_name', 'image3_name', 'image4_name', 'image5_name', 'lot_origin_url']
    fieldsstr = ",".join(fieldnames)
    fp.write(fieldsstr + "\n")
    pagectr = 1
    lotsdata = hindman.getLotsFromPage()
    info = hindman.getInfoFromLotsData(lotsdata, imagepath, downloadimages)
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

# Example: python hindman.py https://hindmanauctions.com/auctions/1113-american-european-art   1113  /Users/saiswarupsahu/freelanceprojectchetan/hindman_1113.csv /Users/saiswarupsahu/freelanceprojectchetan/1-5TNCV9 0 0

# supmit

