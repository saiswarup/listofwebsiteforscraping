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
import http.client
from cryptography.fernet import Fernet
import csv
import unidecode
#http.client.HTTPConnection.debuglevel = 1

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
    fracPattern = re.compile("(\d*)\s*([^\s\.\,;a-zA-Z\d\/]+)")
    fps = re.search(fracPattern, v)
    if fps:
        fpsg = fps.groups()
        wholenumber = fpsg[0]
        fraction = fpsg[1]
        #print(fraction)
        try:
            decimal = round(unicodedata.numeric(fraction), 3)
        except:
            decimal = fraction
            #print(fraction)
        if wholenumber:
            decimalstr = str(decimal).replace("0.", ".")
        else:
            decimalstr = str(decimal)
        value = wholenumber + decimalstr
        return value
    return v


class SothebysBot(object):
    htmltagPattern = re.compile("\<\/?[^\<\>]*\/?\>", re.DOTALL)
    pathEndingWithSlashPattern = re.compile(r"\/$")

    htmlEntitiesDict = {'&nbsp;' : ' ', '&#160;' : ' ', '&amp;' : '&', '&#38;' : '&', '&lt;' : '<', '&#60;' : '<', '&gt;' : '>', '&#62;' : '>', '&apos;' : '\'', '&#39;' : '\'', '&quot;' : '"', '&#34;' : '"'}

    """
    Initialization would include fetching the login page of the email service.
    """
    def __init__(self, auctionurl, auctionnumber=""):
        # Create the opener object(s). Might need more than one type if we need to get pages with unwanted redirects.
        self.opener = urllib.request.build_opener(urllib.request.HTTPHandler(), urllib.request.HTTPSHandler()) # This is my normal opener....
        self.no_redirect_opener = urllib.request.build_opener(urllib.request.HTTPHandler(), urllib.request.HTTPSHandler(), NoRedirectHandler()) # ... and this one won't handle redirects.
        #self.debug_opener = urllib.request.build_opener(urllib.request.HTTPHandler(debuglevel=1))
        # Initialize some object properties.
        self.sessionCookies = ""
        self.httpHeaders = { 'User-Agent' : r'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36',  'Accept' : 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9', 'Accept-Language' : 'en-GB,en-US;q=0.9,en;q=0.8', 'Accept-Encoding' : 'gzip, deflate, br', 'Connection' : 'keep-alive', 'Host' : 'www.sothebys.com'}
        self.httpHeaders['Cache-Control'] = "max-age=0"
        self.httpHeaders['Upgrade-Insecure-Requests'] = "1"
        self.httpHeaders['Sec-Fetch-Dest'] = "document"
        self.httpHeaders['Sec-Fetch-Mode'] = "navigate"
        self.httpHeaders['Sec-Fetch-Site'] = "same-origin"
        self.httpHeaders['Sec-Fetch-User'] = "?1"
        self.httpHeaders['Cookie'] = "optimizelyEndUserId=oeu1620052676437r0.0375360102072031; tracking-preferences={%22version%22:1%2C%22destinations%22:{%22AdWords%22:true%2C%22Adobe%20Analytics%22:true%2C%22Algolia%22:true%2C%22Amplitude%22:true%2C%22Chartbeat%22:true%2C%22DoubleClick%20Floodlight%22:true%2C%22Facebook%20Pixel%22:true%2C%22Google%20Analytics%22:true%2C%22Google%20Tag%20Manager%22:true%2C%22Pinterest%20Tag%22:true%2C%22Promoter.io%22:true%2C%22Twitter%20Ads%22:true%2C%22Visual%20Tagger%22:true%2C%22Zaius%22:true}%2C%22custom%22:{%22marketingAndAnalytics%22:true%2C%22advertising%22:true%2C%22functional%22:true}}; "
        self.homeDir = os.getcwd()
        self.requestUrl = auctionurl
        self.auctionUrl = auctionurl
        parsedUrl = urlparse(self.requestUrl)
        self.baseUrl = parsedUrl.scheme + "://" + parsedUrl.netloc + "/"
        #print(self.requestUrl)
        self.pageRequest = urllib.request.Request(self.requestUrl, headers=self.httpHeaders)
        self.httpproxylist = ['14.52.220.65:8090', '133.88.75.181:80', '91.216.164.251:80', '194.114.128.149:61213', '190.82.91.203:999']
        self.httpsproxylist = ['36.90.118.97:8080', '31.172.177.149:83', '194.233.69.41:443']
        self.socks5proxylist = ['72.195.34.58:4145', '24.249.199.14:57335']
        #self.pageRequest.set_proxy(self.httpproxylist[3], 'http')
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
                #self.pageRequest.set_proxy(self.httpproxylist[3], 'http')
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
        self.currency = "USD"
        self.auctiontitle = ""
        self.auctionlocation = ""
        self.ifctr = 1
        self.aid = auctionnumber


    def _decodeGzippedContent(cls, encoded_content):
        response_stream = io.BytesIO(encoded_content)
        decoded_content = ""
        try:
            gzipper = gzip.GzipFile(fileobj=response_stream)
            decoded_content = gzipper.read()
            decoded_content = decoded_content.decode('utf-8')
        except: # Maybe this isn't gzipped content after all....
            decoded_content = encoded_content
        return(decoded_content)

    _decodeGzippedContent = classmethod(_decodeGzippedContent)


    def _getCookieFromResponse(cls, lastHttpResponse):
        cookies = ""
        if not lastHttpResponse:
            return ""
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
            content = self.pageResponse.read()
            return(content)
        except:
            return bytes("".encode())

    def formatDate(cls, datestr):
        mondict = {'January' : '01', 'February' : '02', 'March' : '03', 'April' : '04', 'May' : '05', 'June' : '06', 'July' : '07', 'August' : '08', 'September' : '09', 'October' : '10', 'November' : '11', 'December' : '12' }
        mondict3 = {'jan.' : '01', 'fév.' : '02', 'mar.' : '03', 'avr.' : '04', 'mai.' : '05', 'jui.' : '06', 'jul.' : '07', 'aoû.' : '08', 'sep.' : '09', 'oct.' : '10', 'nov.' : '11', 'déc.' : '12' }
        datestrcomponents = datestr.split(" ")
        dd = datestrcomponents[0]
        mm = '01'
        if datestrcomponents[1] in mondict.keys():
            mm = mondict[datestrcomponents[1]]
        else:
            mm = mondict3[datestrcomponents[1]]
        yyyy = datestrcomponents[2]
        retdate = mm + "/" + dd + "/" + yyyy
        return retdate

    formatDate = classmethod(formatDate)


    def getLotsFromPage(self):
        baseUrl = "https://www.sothebys.com"
        pageContent = self.currentPageContent
        #print(pageContent)
        soup = BeautifulSoup(self.currentPageContent, features="html.parser")
        alltitletags = soup.find_all("title")
        if alltitletags.__len__() > 0:
            title = alltitletags[0].renderContents().decode('utf-8')
            titleparts = title.split("|")
            if titleparts.__len__() > 0:
                self.auctiontitle = titleparts[0]
        #lotPattern = re.compile('"auction"\:(\{.*\})\}\}\,"showSelectAccountModal"', re.DOTALL)
        lotPattern = re.compile('<script\s+id="__NEXT_DATA__"\s+type="application\/json">(\{"props"\:.*\})<\/script>', re.DOTALL)
        currencyPattern = re.compile('"currency"\:"([A-Z]{3})"\,', re.DOTALL)
        lotjsonsearch = re.search(lotPattern, pageContent)
        currencysearch = re.search(currencyPattern, pageContent)
        if currencysearch:
            self.currency = currencysearch.groups()[0]
        #print(self.currency)
        #apikeyPattern = re.compile('"algoliaSearchKey"\:\{"key"\:"([^"]+)"')
        apikeyPattern = re.compile('"algoliaSearchKey"\:"([^"]+)"')
        apis = re.search(apikeyPattern, pageContent)
        if apis:
            self.algolia_api_key = apis.groups()[0]
        lotjson = {}
        lotsdata = []
        trailbracePattern = re.compile("\}+$")
        if lotjsonsearch:
            ljsg = lotjsonsearch.groups()[0]
            #ljsg = trailbracePattern.sub("", ljsg)
            #ljsg = ljsg + "}]}"
            #print(ljsg)
            lotjson = json.loads(ljsg)
            algoliajson = lotjson['props']['pageProps']['algoliaJson']
            if 'hits' in algoliajson.keys():
                #lotsdata = lotjson['lots']
                lotsdata = algoliajson['hits']
                #print(lotsdata[0]['auctionId'])
                if lotsdata.__len__() > 0:
                    self.aid = lotsdata[0]['auctionId']
                return lotsdata
        return lotsdata
        

    def getDetailsPage(self, detailUrl):
        self.requestUrl = detailUrl
        self.pageRequest = urllib.request.Request(self.requestUrl, headers=self.httpHeaders)
        #self.pageRequest.set_proxy(self.httpproxylist[3], 'http')
        self.pageResponse = None
        self.postData = {}
        try:
            self.pageResponse = self.opener.open(self.pageRequest, timeout=10)
            headers = self.pageResponse.getheaders()
        except:
            print ("Couldn't fetch page due to limited connectivity. Please check your internet connection and try again. %s"%sys.exc_info()[1].__str__())
        self.httpHeaders["Referer"] = self.auctionUrl
        self.sessionCookies = self.__class__._getCookieFromResponse(self.pageResponse)
        self.httpHeaders["Cookie"] = self.sessionCookies
        self.currentPageContent = self.__class__._decodeGzippedContent(self.getPageContent())
        return self.currentPageContent


    def fractionToDecimalSize(self, sizestring):
        sizestringparts = sizestring.split("x")
        if sizestringparts.__len__() < 1:
            sizestringparts = sizestring.split("by")
        unitPattern = re.compile("(\s*(inches)|(cm)\s*$)", re.IGNORECASE)
        ups = re.search(unitPattern, sizestringparts[-1])
        unit = ""
        if ups:
            upsg = ups.groups()
            unit = upsg[0]
        sizestringparts[-1] = unitPattern.sub("", sizestringparts[-1])
        decimalsizeparts = []
        beginspacePattern = re.compile("^\s+")
        endspacePattern = re.compile("\s+$")
        middlespacePattern = re.compile("\s+")
        for szpart in sizestringparts:
            szpart = szpart.replace(":", "")
            szpart = beginspacePattern.sub("", szpart)
            szpart = endspacePattern.sub("", szpart)
            szpart = middlespacePattern.sub("", szpart)
            d_szpart = unicodefraction_to_decimal(szpart)
            decimalsizeparts.append(d_szpart)
        decimalsize = " x ".join(decimalsizeparts)
        decimalsize += " " + unit
        return decimalsize


    def renameImagefile(self, basepath, imagefilename, mappedImagename):
        oldfilename = basepath + "/" + imagefilename
        newfilename = basepath + "/" + mappedImagename
        os.rename(oldfilename, newfilename)


    def encryptFilename(self, filename):
        k = Fernet.generate_key()
        f = Fernet(k)
        encfilename = f.encrypt(filename.encode())
        return encfilename


    def getsize(self, lotdetailspart):
        beginSpacePattern = re.compile("^\s+", re.DOTALL)
        newlinesPattern = re.compile("\\r?\\n|\\r", re.DOTALL)
        brPattern = re.compile("<br\s*\/?>", re.IGNORECASE|re.DOTALL)
        sizePattern_sp1 = re.compile("([\d\.]*\s*x\s*[\d\.]*\s*[x]*\s*[\d\.]*\s+cm)", re.DOTALL|re.IGNORECASE)
        sizePattern_sp2 = re.compile("([\d\.]+\s*mm)", re.DOTALL|re.IGNORECASE)
        sizePattern = re.compile("([^a-z\:]+\s+by\s+[^a-z]+in[ches]*\.)[\s;]{0,1}", re.DOTALL|re.IGNORECASE)
        sizePattern4 = re.compile("([^a-z\:]+\s+by\s+[^a-z]+\s+by\s+[^a-z]+\s+in[ches]*\.)[\s;]{0,1}", re.DOTALL|re.IGNORECASE)
        #sizePattern2 = re.compile("Height.*\(([\d\.]+\s+cm)\)", re.DOTALL|re.IGNORECASE)
        sizePattern2 = re.compile("Height\s*\:?\s*([^a-z]+\s+in[ches]*\.?)[\s;]{0,1}", re.DOTALL|re.IGNORECASE)
        sizePattern3 = re.compile("([^a-z]+\s+by\s+[^a-z]+\s+in[ches]*\.?)[\s;]{0,1}", re.DOTALL|re.IGNORECASE)
        sizePattern5 = re.compile("([^a-z]+\s+by\s+[^a-z]+\s+by\s+[^a-z]+\s+in[ches]*\.)[\s;]{0,1}", re.DOTALL|re.IGNORECASE)
        sizePattern6 = re.compile("Height\s*[\w\s]+\:?\s+([^a-z]+\s+in[ches]*\.?)[\s;]{0,1}", re.DOTALL|re.IGNORECASE)
        sizePattern7 = re.compile("(inches\s+[^a-z]+\s+by\s+[^a-z]+)[\s;]{0,1}", re.DOTALL|re.IGNORECASE)
        sizePattern8 = re.compile("(inches\s+[^a-z]+\s+by\s+[^a-z]+\s+by\s+[^a-z]+)[\s;]{0,1}", re.DOTALL|re.IGNORECASE)
        sizePattern9 = re.compile("H\.\s*[\d\.]+\s*cm[\s;]+([^\s]+\s+in)\.", re.DOTALL|re.IGNORECASE)
        sizePattern9_5 = re.compile("([\d\.\s\/]+x[\s\d\.\/]+\s*in)\.?", re.DOTALL|re.IGNORECASE) # Had to insert fractional suffix.. Ha ha...
        sizePattern9_5a = re.compile("[\s;]+([\d\s\.\/]+\s+in)\.", re.DOTALL|re.IGNORECASE)
        sizePattern9_5b = re.compile(";\s+(.*?\s+in)\.", re.DOTALL|re.IGNORECASE)
        sizePattern10 = re.compile("[\s;]+([^\s]+\s+in)\.", re.DOTALL|re.IGNORECASE)
        sizePattern11a = re.compile("([\d\sx\.,]+cm)\s+\(unframed\)", re.DOTALL|re.IGNORECASE)
        sizePattern11b = re.compile("([\d\sx\.,]+cm)\s+\(framed\)", re.DOTALL|re.IGNORECASE)
        sizePattern11c = re.compile("([\d\sx\.,]+cm)\s*", re.DOTALL|re.IGNORECASE)
        sizePattern12 = re.compile("([\d\s\.]+\s+by\s+[\d\.\s]+\s+mm)\s*", re.DOTALL|re.IGNORECASE)
        sizePattern12_a = re.compile("([\d\s\.]+\s+by\s+[\d\.\s]+\s+by\s+[\d\.\s]+\s*mm)\s*", re.DOTALL|re.IGNORECASE)
        sizePattern13 = re.compile("([\d\s\.]+\s+by\s+[\d\.\s]+\s*cm)", re.DOTALL|re.IGNORECASE)
        sheetsizePattern = re.compile("sheet\:\s+([^a-z\:]+\s+by\s+[^a-z]+in[ches]{0,4}\.?)[\s;]{0,1}", re.DOTALL|re.IGNORECASE)
        sheetsizePattern2 = re.compile("sheet\:\s+([^a-z\:]+\s+by\s+[^a-z]+\s+by\s+[^a-z]+\s+in[ches]{0,4}\.?)[\s;]{0,1}", re.DOTALL|re.IGNORECASE)
        sheetsizePattern3 = re.compile("sheet\:\s+\d+\s+by\s+\d+\s+[cm]{0,2}\s+([^a-z\:]+\s+by\s+[^a-z]+in[ches]{0,4}\.?)[\s;]{0,1}", re.DOTALL|re.IGNORECASE)
        sheetsizePattern4 = re.compile("sheet\:\s+\d+\s+by\s+\d+\s+by\s+\d+\s+[cm]{0,2}\s+([^a-z\:]+\s+by\s+[^a-z]+\s+by\s+[^a-z]+\s+in[ches]{0,4}\.?)[\s;]{0,1}", re.DOTALL|re.IGNORECASE)
        sheetsizePattern5 = re.compile("sheet\:\s+(\d+\s+by\s+\d+\s*(by)?\s*\d*\s*mm)", re.DOTALL|re.IGNORECASE)
        heightPattern = re.compile("Height.*\:", re.DOTALL|re.IGNORECASE)
        size, category, sheetsize = "", "2d", ""
        zpss = re.search(sizePattern_sp1, lotdetailspart)
        if zpss and size == "":
            zpsg = zpss.groups()
            size = zpsg[0]
            size = heightPattern.sub("", size)
        zps = re.search(sizePattern, lotdetailspart)
        if zps and size == "":
            zpsg = zps.groups()
            size = zpsg[0]
            size = heightPattern.sub("", size)
            size = size.replace("Framed:", "")
            sizeparts = size.split("by")
            if sizeparts.__len__() != 2:
                category = '3d'
        zps4 = re.search(sizePattern4, lotdetailspart)
        if zps4 and size == "":
            zpsg4 = zps4.groups()
            size = zpsg4[0]
            size = heightPattern.sub("", size)
            size = size.replace("Framed:", "")
            sizeparts = size.split("by")
            if sizeparts.__len__() != 2:
                category = '3d'
        zps2 = re.search(sizePattern2, lotdetailspart)
        if zps2 and size == "":
            zpsg2 = zps2.groups()
            size = zpsg2[0]
            size = heightPattern.sub("", size)
            size = size.replace("Framed:", "")
            category = '3d'
        zps3 = re.search(sizePattern3, lotdetailspart)
        if zps3 and size == "":
            zpsg3 = zps3.groups()
            size = zpsg3[0]
            size = heightPattern.sub("", size)
            size = size.replace("Framed:", "")
            sizeparts = size.split("by")
            if sizeparts.__len__() != 2:
                category = '3d'
        zps5 = re.search(sizePattern5, lotdetailspart)
        if zps5 and size == "":
            zpsg5 = zps5.groups()
            size = zpsg5[0]
            size = heightPattern.sub("", size)
            size = size.replace("Framed:", "")
            sizeparts = size.split("by")
            if sizeparts.__len__() != 2:
                category = '3d'
        zps6 = re.search(sizePattern6, lotdetailspart)
        if zps6 and size == "":
            zpsg6 = zps6.groups()
            size = zpsg6[0]
            size = heightPattern.sub("", size)
            size = size.replace("Framed:", "")
            sizeparts = size.split("by")
            if sizeparts.__len__() != 2:
                category = '3d'
        zps7 = re.search(sizePattern7, lotdetailspart)
        if zps7 and size == "":
            zpsg7 = zps7.groups()
            size = zpsg7[0]
            size = heightPattern.sub("", size)
            size = size.replace("Framed:", "")
            sizeparts = size.split("by")
            if sizeparts.__len__() != 2:
                category = '3d'
        zps8 = re.search(sizePattern8, lotdetailspart)
        if zps8 and size == "":
            zpsg8 = zps8.groups()
            size = zpsg8[0]
            size = heightPattern.sub("", size)
            size = size.replace("Framed:", "")
            sizeparts = size.split("by")
            if sizeparts.__len__() != 2:
                category = '3d'
        zps9 = re.search(sizePattern9, lotdetailspart)
        if zps9 and size == "":
            zpsg9 = zps9.groups()
            size = zpsg9[0]
            size = heightPattern.sub("", size)
            size = size.replace("Framed:", "")
            sizeparts = size.split("by")
            if sizeparts.__len__() != 2:
                category = '3d'
        zps9_5 = re.search(sizePattern9_5, lotdetailspart)
        if zps9_5 and size == "":
            zpsg9_5 = zps9_5.groups()
            size = zpsg9_5[0]
            size = size.replace("Framed:", "")
            sizeparts = size.split("x")
            if sizeparts.__len__() != 2:
                category = '3d'
        zps9_5b = re.search(sizePattern9_5b, lotdetailspart)
        if zps9_5b and size == "":
            zpsg9_5b = zps9_5b.groups()
            size = zpsg9_5b[0]
            category = '3d'
        zps9_5a = re.search(sizePattern9_5a, lotdetailspart)
        if zps9_5a and size == "":
            zpsg9_5a = zps9_5a.groups()
            size = zpsg9_5a[0]
            size = size.replace("Framed:", "")
            category = '3d'
        zps10 = re.search(sizePattern10, lotdetailspart)
        if zps10 and size == "":
            zpsg10 = zps10.groups()
            size = zpsg10[0]
            size = heightPattern.sub("", size)
            size = size.replace("Framed:", "")
            sizeparts = size.split("by")
            if sizeparts.__len__() != 2:
                category = '3d'
        zps11a = re.search(sizePattern11a, lotdetailspart)
        if zps11a and sheetsize == "":
            zpsg11a = zps11a.groups()
            size = zpsg11a[0]
            size = heightPattern.sub("", size)
            size = size.replace("Framed:", "")
            sheetsize = size
        zps11b = re.search(sizePattern11b, lotdetailspart)
        if zps11b and size == "":
            zpsg11b = zps11b.groups()
            size = zpsg11b[0]
            size = heightPattern.sub("", size)
            size = size.replace("Framed:", "")
            sizeparts = size.split("x")
            if sizeparts.__len__() != 2:
                category = '3d'
        zps11c = re.search(sizePattern11c, lotdetailspart)
        if zps11c and size == "":
            zpsg11c = zps11c.groups()
            size = zpsg11c[0]
            size = heightPattern.sub("", size)
            size = size.replace("Framed:", "")
            sizeparts = size.split("x")
            if sizeparts.__len__() != 2:
                category = '3d'
        zps12_a = re.search(sizePattern12_a, lotdetailspart)
        if zps12_a and size == "":
            zpsg12_a = zps12_a.groups()
            size = zpsg12_a[0]
            size = heightPattern.sub("", size)
            size = size.replace("Framed:", "")
            sizeparts = size.split("by")
            if sizeparts.__len__() != 2:
                category = '3d'
        zps12 = re.search(sizePattern12, lotdetailspart)
        if zps12 and size == "":
            zpsg12 = zps12.groups()
            size = zpsg12[0]
            size = heightPattern.sub("", size)
            size = size.replace("Framed:", "")
            sizeparts = size.split("by")
            if sizeparts.__len__() != 2:
                category = '3d'
        zps13 = re.search(sizePattern13, lotdetailspart)
        if zps13 and size == "":
            zpsg13 = zps13.groups()
            size = zpsg13[0]
            size = heightPattern.sub("", size)
            size = size.replace("Framed:", "")
            sizeparts = size.split("by")
            if sizeparts.__len__() != 2:
                category = '3d'
            #print(size)
        if size != "":
            size = size.replace(",",".")
            size = beginSpacePattern.sub("", size)
            size = size.replace("by", "x")
            size = size.replace("; ", "")
            begindotPattern = re.compile("^\.+")
            #size = begindotPattern.sub("", size)
            size = beginSpacePattern.sub("", size)
        ssps = re.search(sheetsizePattern, lotdetailspart)
        if ssps and sheetsize == "":
            sspsg = ssps.groups()
            sheetsize = sspsg[0]
            sheetsize = sheetsize.replace("by", "x")
        ssps2 = re.search(sheetsizePattern2, lotdetailspart)
        if ssps2 and sheetsize == "":
            sspsg2 = ssps2.groups()
            sheetsize = sspsg2[0]
            sheetsize = sheetsize.replace("by", "x")
        ssps3 = re.search(sheetsizePattern3, lotdetailspart)
        if ssps3 and sheetsize == "":
            sspsg3 = ssps3.groups()
            sheetsize = sspsg3[0]
            sheetsize = sheetsize.replace("by", "x")
        ssps4 = re.search(sheetsizePattern4, lotdetailspart)
        if ssps4 and sheetsize == "":
            sspsg4 = ssps4.groups()
            sheetsize = sspsg4[0]
            sheetsize = sheetsize.replace("by", "x")
        ssps5 = re.search(sheetsizePattern5, lotdetailspart)
        if ssps5 and sheetsize == "":
            sspsg5 = ssps5.groups()
            sheetsize = sspsg5[0]
            sheetsize = sheetsize.replace("by", "x")
            sheetsize = beginSpacePattern.sub("", sheetsize)
        return (size, sheetsize, category)


    def getImagenameFromUrl(self, imageUrl):
        urlparts = imageUrl.split("/")
        imagefilepart = urlparts[-1]
        imagefilenameparts = imagefilepart.split("?")
        imagefilename = imagefilenameparts[0]
        return imagefilename

    
    def parseDetailPage(self, detailsPage, lotno, imagepath, artistname, artworkname, downloadimages):
        baseUrl = "https://www.sothebys.com"
        detailData = {}
        beginSpacePattern = re.compile("^\s+", re.DOTALL)
        newlinesPattern = re.compile("\\r?\\n|\\r", re.DOTALL)
        brPattern = re.compile("<br\s*\/?>", re.IGNORECASE|re.DOTALL)
        soup = BeautifulSoup(detailsPage, features="html.parser")
        lotdetailsdiv = soup.find_all("div", {'id' : 'LotDetails'})
        classPattern = re.compile("label\-module_label16Medium__2HDfw")
        soldpriceptags = soup.find_all("p", {'class' : classPattern})
        if soldpriceptags.__len__() > 2:
            detailData['ALTERNATE_SOLD_PRICE'] = soldpriceptags[1].renderContents().decode("utf-8") + " " + soldpriceptags[2].renderContents().decode("utf-8")
            if not soldpriceptags[1].renderContents().decode("utf-8"):
                detailData['ALTERNATE_SOLD_PRICE'] = ""
            #print(detailData['ALTERNATE_SOLD_PRICE'])
        signedPattern = re.compile("\s+signed", re.DOTALL|re.IGNORECASE)
        signedPattern2 = re.compile("^signed", re.DOTALL|re.IGNORECASE)
        signedPattern3 = re.compile("dated", re.DOTALL|re.IGNORECASE)
        sizePattern_sp1 = re.compile("([\d\.]*\s*x\s*[\d\.]*\s*[x]*\s*[\d\.]*\s+cm)", re.DOTALL|re.IGNORECASE)
        sizePattern_sp2 = re.compile("([\d\.]+\s*mm)", re.DOTALL|re.IGNORECASE)
        sizePattern = re.compile("([^a-z\:]+\s+by\s+[^a-z]+in[ches]*\.)[\s;]{0,1}", re.DOTALL|re.IGNORECASE)
        sizePattern4 = re.compile("([^a-z\:]+\s+by\s+[^a-z]+\s+by\s+[^a-z]+\s+in[ches]*\.)[\s;]{0,1}", re.DOTALL|re.IGNORECASE)
        #sizePattern2 = re.compile("Height.*\(([\d\.]+\s+cm)\)", re.DOTALL|re.IGNORECASE)
        sizePattern2 = re.compile("Height\s*\:?\s*([^a-z]+\s+in[ches]*\.?)[\s;]{0,1}", re.DOTALL|re.IGNORECASE)
        sizePattern3 = re.compile("([^a-z]+\s+by\s+[^a-z]+\s+in[ches]*\.?)[\s;]{0,1}", re.DOTALL|re.IGNORECASE)
        sizePattern5 = re.compile("([^a-z]+\s+by\s+[^a-z]+\s+by\s+[^a-z]+\s+in[ches]*\.)[\s;]{0,1}", re.DOTALL|re.IGNORECASE)
        sizePattern6 = re.compile("Height\s*[\w\s]+\:?\s+([^a-z]+\s+in[ches]*\.?)[\s;]{0,1}", re.DOTALL|re.IGNORECASE)
        sizePattern7 = re.compile("(inches\s+[^a-z]+\s+by\s+[^a-z]+)[\s;]{0,1}", re.DOTALL|re.IGNORECASE)
        sizePattern8 = re.compile("(inches\s+[^a-z]+\s+by\s+[^a-z]+\s+by\s+[^a-z]+)[\s;]{0,1}", re.DOTALL|re.IGNORECASE)
        sizePattern9 = re.compile("H\.\s*[\d\.]+\s*cm[\s;]+([^\s]+\s+in)\.", re.DOTALL|re.IGNORECASE)
        sizePattern9_5 = re.compile("([\d\.\s\/]+x[\s\d\.\/]+\s*in)\.?", re.DOTALL|re.IGNORECASE) # Had to insert fractional suffix.. Ha ha...
        sizePattern9_5a = re.compile("[\s;]+([\d\s\.\/]+\s+in)\.", re.DOTALL|re.IGNORECASE)
        sizePattern9_5b = re.compile(";\s+(.*?\s+in)\.", re.DOTALL|re.IGNORECASE)
        sizePattern10 = re.compile("[\s;]+([^\s]+\s+in)\.", re.DOTALL|re.IGNORECASE)
        sizePattern11a = re.compile("([\d\sx\.,]+cm)\s+\(unframed\)", re.DOTALL|re.IGNORECASE)
        sizePattern11b = re.compile("([\d\sx\.,]+cm)\s+\(framed\)", re.DOTALL|re.IGNORECASE)
        sizePattern11c = re.compile("([\d\sx\.,]+cm)\s*", re.DOTALL|re.IGNORECASE)
        sizePattern12 = re.compile("([\d\s\.]+\s+by\s+[\d\.\s]+\s+mm)\s*", re.DOTALL|re.IGNORECASE)
        sizePattern13 = re.compile("([\d\s\.]+\s+by\s+[\d\.\s]+\s*cm)", re.DOTALL|re.IGNORECASE)
        sheetsizePattern = re.compile("sheet\:\s+([^a-z\:]+\s+by\s+[^a-z]+in[ches]{0,4}\.?)[\s;]{0,1}", re.DOTALL|re.IGNORECASE)
        sheetsizePattern2 = re.compile("sheet\:\s+([^a-z\:]+\s+by\s+[^a-z]+\s+by\s+[^a-z]+\s+in[ches]{0,4}\.?)[\s;]{0,1}", re.DOTALL|re.IGNORECASE)
        sheetsizePattern3 = re.compile("sheet\:\s+\d+\s+by\s+\d+\s+[cm]{0,2}\s+([^a-z\:]+\s+by\s+[^a-z]+in[ches]{0,4}\.?)[\s;]{0,1}", re.DOTALL|re.IGNORECASE)
        sheetsizePattern4 = re.compile("sheet\:\s+\d+\s+by\s+\d+\s+by\s+\d+\s+[cm]{0,2}\s+([^a-z\:]+\s+by\s+[^a-z]+\s+by\s+[^a-z]+\s+in[ches]{0,4}\.?)[\s;]{0,1}", re.DOTALL|re.IGNORECASE)
        sheetsizePattern5 = re.compile("sheet\:\s+(\d+\s+by\s+\d+\s*(by)?\s*\d*\s*mm)", re.DOTALL|re.IGNORECASE)
        mediumPattern = re.compile("(\s+gold)|(silver)|(brass)|(bronze)|(wood)|(porcelain)|(stone)|(marble)|(metal)|(steel)|(iron)|(glass)|(plexiglas)|(chromogenic)|(paper)|(canvas)|(masonite)|(newsprint)|(silkscreen)|(parchment)|(linen)|(inkjet)|(ink\s+jet)|(pigment)|(\stin\s)|(photogravure)|(^oil\s+)|(oil\s+)|(\s+panel\s+)|(terracotta)|(ivory)|(\s+oak\s+)|(^oak\s+)|(\s+oak$)|(alabaster)|(chalk)|(\s+ink\s+)|(ceramic)|(acrylic)|(aluminium)|(aquatint)|(linoleum)|(etching)|(collotype)|(lithograph)|(drypoint)|(arches\s+wove)|(pochoir)|(screenprint)|(digital\s+print)|(print\s+in\s+colou?rs)|(photograph)|(resin)|(mixed\s+media)|(laser\s+disk)|(perspex)|(aluminum)", re.DOTALL|re.IGNORECASE)
        yearPattern = re.compile("[io]n\s+(\d{4})\s*[\/\-]?(\d{0,4})", re.DOTALL|re.IGNORECASE)
        birthdeathyearPattern = re.compile("b?\w*\.?\s*(\d{4})\s*\-?\s*(\d{0,4})", re.DOTALL)
        authenticityPattern = re.compile("([^\.]+authenticity[^\.]+)\.", re.DOTALL|re.IGNORECASE)
        inscribedPattern = re.compile("Inscribed", re.DOTALL)
        conceivedPattern = re.compile("conceived\s+in\s+(\d{4})\-?(\d{0,4})", re.DOTALL|re.IGNORECASE)
        conditionPattern = re.compile("condition\s+report", re.DOTALL|re.IGNORECASE)
        editionPattern = re.compile("edition[ed]*\s+(\d+)/(\d+)", re.DOTALL|re.IGNORECASE)
        editionPattern2 = re.compile("edition", re.DOTALL|re.IGNORECASE)
        editionPattern3 = re.compile("numbered\s+[\d\/]+", re.DOTALL|re.IGNORECASE)
        heightPattern = re.compile("Height.*\:", re.DOTALL|re.IGNORECASE)
        bdPattern1 = re.compile("(\d{4})\s*\-\s*(\d{4})")
        bdPattern2 = re.compile("b\.\s*(\d{4})")
        multispacePattern = re.compile("\s{2,}")
        begindotPattern = re.compile("^\s*\.\s*")
        matcatdict_en = {}
        matcatdict_fr = {}
        with open("docs/fineart_materials.csv", newline='') as mapfile:
        #with open("/root/artwork/deploydirnew/docs/fineart_materials.csv", newline='') as mapfile:
            mapreader = csv.reader(mapfile, delimiter=",", quotechar='"')
            for maprow in mapreader:
                matcatdict_en[maprow[1]] = maprow[3]
                matcatdict_fr[maprow[2]] = maprow[3]
        mapfile.close()
        """
        Post 2021 December, Sotheby has changed this data to json format, sent to the page as json data in the HTML page.
        """
        if lotdetailsdiv.__len__() == 0 or lotdetailsdiv.__len__() == 1: # quick fix. Nowadays, we do get lotdetailsdiv.__len__() greater than 0 and in such cases we should not be executing this code. The correct way to fix this is to remove the if condition altogether and execute the code for all cases. No time for that right now.
            lotdetailPattern = re.compile("\"lotDetailsJson\"\:(\{.*?\}\}\})")
            try:
                ldps = re.search(lotdetailPattern, detailsPage.decode('utf-8'))
            except:
                print("Error: %s"%sys.exc_info()[1].__str__())
                ldps = re.search(lotdetailPattern, detailsPage)
            if ldps:
                tdata = ldps.groups()[0]
                jdata = json.loads(tdata)
                #print(jdata['data']['lotDetails']['description'])
                s = BeautifulSoup(jdata['data']['lotDetails']['description'], features="html.parser")
                allparas = s.find_all("p")
                itemsdict = jdata['data']['lotDetails']['items'][0]
                detailData['artwork_provenance'] = ""
                detailData['artwork_exhibited'] = ""
                detailData['artwork_literature'] = ""
                if 'provenance' in itemsdict.keys() and itemsdict['provenance'] is not None and itemsdict['provenance'] != "":
                    detailData['artwork_provenance'] = itemsdict['provenance']
                if 'literature' in itemsdict.keys() and itemsdict['literature'] is not None and itemsdict['literature'] != "":
                    detailData['artwork_literature'] = itemsdict['literature']
                if 'exhibited' in itemsdict.keys() and itemsdict['exhibited'] is not None and itemsdict['exhibited'] != "":
                    detailData['artwork_exhibited'] = itemsdict['exhibited']
                try:
                    images = jdata['data']['lotDetails']['media']['images']
                except:
                    images = []
                #print(images)
                detailData['artwork_images1'] = ""
                detailData['image1_name'] = ""
                additionalimageurls = []
                for img in images:
                    renditions = img['renditions']
                    for rendition in renditions:
                        imgsize = rendition['imageSize']
                        #print(imgsize)
                        if imgsize == "ExtraLarge" or imgsize == "Large" or imgsize == "Medium" or imgsize == "Original":
                            url = rendition['url']
                            urlPattern = re.compile("\?url=(.*)$")
                            ups = re.search(urlPattern, url)
                            if ups:
                                if detailData['artwork_images1'] == "":
                                    defaultimageurl = ups.groups()[0]
                                    defaultimageurl = defaultimageurl.replace("%3A", ":").replace("%2F", "/")
                                    #print(defaultimageurl)
                                    imagename1 = self.getImagenameFromUrl(defaultimageurl)
                                    imagename1 = str(imagename1)
                                    imagename1 = imagename1.replace("b'", "").replace("'", "")
                                    auctiontitle = self.auctiontitle.replace(" ", "_")
                                    processedAuctionTitle = auctiontitle.replace(" ", "_")
                                    processedArtistName = artistname.replace(" ", "_")
                                    processedArtistName = unidecode.unidecode(processedArtistName)
                                    processedArtworkName = artworkname.replace(" ", "_")
                                    processedArtworkName = unidecode.unidecode(processedArtworkName)
                                    auction_number = self.saleno
                                    sublot_number = ""
                                    newname1 = auction_number + "__" + processedArtistName + "__" + str(lotno) + "_a"
                                    #encryptedFilename = self.encryptFilename(newname1)
                                    encryptedFilename = newname1
                                    imagepathparts = defaultimageurl.split("/")
                                    defimageurl = "/".join(imagepathparts[:-2])
                                    encryptedFilename = str(encryptedFilename).replace("b'", "")
                                    encryptedFilename = str(encryptedFilename).replace("'", "")
                                    detailData['image1_name'] = str(encryptedFilename) + ".jpg"
                                    detailData['artwork_images1'] = defaultimageurl
                                    #self.getImage(detailData['artwork_images1'], imagepath, downloadimages)
                                    if downloadimages == "1":
                                        encryptedFilename = str(encryptedFilename) + "-a.jpg"
                                        self.renameImagefile(imagepath, imagename1, encryptedFilename)
                                else:
                                    altimgurl = ups.groups()[0]
                                    altimgurl = altimgurl.replace("%3A", ":").replace("%2F", "/")
                                    #print(altimgurl)
                                    additionalimageurls.append(altimgurl)
                            else:
                                if detailData['artwork_images1'] == "":
                                    defaultimageurl = url
                                    defaultimageurl = defaultimageurl.replace("%3A", ":").replace("%2F", "/")
                                    #print(defaultimageurl)
                                    imagename1 = self.getImagenameFromUrl(defaultimageurl)
                                    imagename1 = str(imagename1)
                                    imagename1 = imagename1.replace("b'", "").replace("'", "")
                                    auctiontitle = self.auctiontitle.replace(" ", "_")
                                    processedAuctionTitle = auctiontitle.replace(" ", "_")
                                    processedArtistName = artistname.replace(" ", "_")
                                    processedArtistName = unidecode.unidecode(processedArtistName)
                                    processedArtworkName = artworkname.replace(" ", "_")
                                    processedArtworkName = unidecode.unidecode(processedArtworkName)
                                    auction_number = self.saleno
                                    sublot_number = ""
                                    newname1 = auction_number + "__" + processedArtistName + "__" + str(lotno) + "_a"
                                    #encryptedFilename = self.encryptFilename(newname1)
                                    encryptedFilename = newname1
                                    imagepathparts = defaultimageurl.split("/")
                                    defimageurl = "/".join(imagepathparts[:-2])
                                    encryptedFilename = str(encryptedFilename).replace("b'", "")
                                    encryptedFilename = str(encryptedFilename).replace("'", "")
                                    detailData['image1_name'] = str(encryptedFilename) + ".jpg"
                                    detailData['artwork_images1'] = defaultimageurl
                                    #self.getImage(detailData['artwork_images1'], imagepath, downloadimages)
                                    if downloadimages == "1":
                                        encryptedFilename = str(encryptedFilename) + "-a.jpg"
                                        self.renameImagefile(imagepath, imagename1, encryptedFilename)
                                else:
                                    altimgurl = url
                                    altimgurl = altimgurl.replace("%3A", ":").replace("%2F", "/")
                                    #print(altimgurl)
                                    additionalimageurls.append(altimgurl)
                imgctr = 2
                if additionalimageurls.__len__() > 0:
                    altimage2 = additionalimageurls[0]
                    imagename1 = self.getImagenameFromUrl(altimage2)
                    imagename1 = str(imagename1)
                    imagename1 = imagename1.replace("b'", "").replace("'", "")
                    altimage2parts = altimage2.split("/")
                    altimageurl = "/".join(altimage2parts[:-2])
                    processedArtistName = artistname.replace(" ", "_")
                    processedArtistName = unidecode.unidecode(processedArtistName)
                    processedArtworkName = artworkname.replace(" ", "_")
                    processedArtworkName = unidecode.unidecode(processedArtworkName)
                    sublot_number = ""
                    #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + auction_number + "__" + str(lotno) + "__" + sublot_number
                    auction_number = self.saleno
                    newname1 = auction_number + "__" + processedArtistName + "__" + str(lotno) + "_b"
                    #encryptedFilename = self.encryptFilename(newname1)
                    encryptedFilename = newname1
                    detailData['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
                    detailData['artwork_images' + str(imgctr)] = altimage2
                    #self.getImage(detailData['artwork_images' + str(imgctr)], imagepath, downloadimages)
                    imgctr += 1
                if additionalimageurls.__len__() > 1:
                    altimage3 = additionalimageurls[1]
                    imagename1 = self.getImagenameFromUrl(altimage3)
                    imagename1 = str(imagename1)
                    imagename1 = imagename1.replace("b'", "").replace("'", "")
                    altimage3parts = altimage3.split("/")
                    altimageurl = "/".join(altimage3parts[:-2])
                    processedArtistName = artistname.replace(" ", "_")
                    processedArtistName = unidecode.unidecode(processedArtistName)
                    processedArtworkName = artworkname.replace(" ", "_")
                    processedArtworkName = unidecode.unidecode(processedArtworkName)
                    sublot_number = ""
                    #newname3 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + auction_number + "__" + str(lotno) + "__" + sublot_number
                    auction_number = self.saleno
                    newname3 = auction_number + "__" + processedArtistName + "__" + str(lotno) + "_c"
                    #encryptedFilename = self.encryptFilename(newname3)
                    encryptedFilename = newname3
                    detailData['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
                    detailData['artwork_images' + str(imgctr)] = altimage3
                    #self.getImage(detailData['artwork_images' + str(imgctr)], imagepath, downloadimages)
                    imgctr += 1
                if additionalimageurls.__len__() > 2:
                    altimage4 = additionalimageurls[2]
                    imagename1 = self.getImagenameFromUrl(altimage4)
                    imagename1 = str(imagename1)
                    imagename1 = imagename1.replace("b'", "").replace("'", "")
                    altimage4parts = altimage4.split("/")
                    altimageurl = "/".join(altimage4parts[:-2])
                    processedArtistName = artistname.replace(" ", "_")
                    processedArtistName = unidecode.unidecode(processedArtistName)
                    processedArtworkName = artworkname.replace(" ", "_")
                    processedArtworkName = unidecode.unidecode(processedArtworkName)
                    sublot_number = ""
                    #newname4 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + auction_number + "__" + str(lotno) + "__" + sublot_number
                    auction_number = self.saleno
                    newname4 = auction_number + "__" + processedArtistName + "__" + str(lotno) + "_d"
                    #encryptedFilename = self.encryptFilename(newname4)
                    encryptedFilename = newname4
                    detailData['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
                    detailData['artwork_images' + str(imgctr)] = altimage4
                    #self.getImage(detailData['artwork_images' + str(imgctr)], imagepath, downloadimages)
                    imgctr += 1
                if additionalimageurls.__len__() > 3:
                    altimage5 = additionalimageurls[3]
                    imagename1 = self.getImagenameFromUrl(altimage5)
                    imagename1 = str(imagename1)
                    imagename1 = imagename1.replace("b'", "").replace("'", "")
                    altimage5parts = altimage5.split("/")
                    altimageurl = "/".join(altimage5parts[:-2])
                    processedArtistName = artistname.replace(" ", "_")
                    processedArtistName = unidecode.unidecode(processedArtistName)
                    processedArtworkName = artworkname.replace(" ", "_")
                    processedArtworkName = unidecode.unidecode(processedArtworkName)
                    sublot_number = ""
                    #newname5 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + auction_number + "__" + str(lotno) + "__" + sublot_number
                    auction_number = self.saleno
                    newname5 = auction_number + "__" + processedArtistName + "__" + str(lotno) + "_e"
                    #encryptedFilename = self.encryptFilename(newname5)
                    encryptedFilename = newname5
                    detailData['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
                    detailData['artwork_images' + str(imgctr)] = altimage5
                    #self.getImage(detailData['artwork_images' + str(imgctr)], imagepath, downloadimages)
                    if downloadimages == "1":
                        encryptedFilename = str(encryptedFilename) + "-b.jpg"
                        self.renameImagefile(imagepath, imagename1, encryptedFilename)
                for para in allparas:
                    paracontent = para.renderContents().decode('utf-8')
                    paracontent = self.__class__.htmltagPattern.sub("", paracontent)
                    paracontent = paracontent.replace("\n", "").replace("\r", "")
                    paracontent = newlinesPattern.sub("", paracontent)
                    paracontent = multispacePattern.sub(" ", paracontent)
                    bdps1 = re.search(bdPattern1, paracontent)
                    bdps2 = re.search(bdPattern2, paracontent)
                    if 'artist_birth' not in detailData.keys() and bdps1:
                        detailData['artist_birth'] = bdps1.groups()[0]
                        detailData['artist_death'] = bdps1.groups()[1]
                    if 'artist_birth' not in detailData.keys() and bdps2:
                        detailData['artist_birth'] = bdps2.groups()[0]
                        detailData['artist_death'] = ""
                    sps1 = re.search(signedPattern, paracontent)
                    sps2 = re.search(signedPattern2, paracontent)
                    sps3 = re.search(signedPattern3, paracontent)
                    if 'artwork_markings' not in detailData.keys() and (sps1 or sps2 or sps3):
                        detailData['artwork_markings'] = paracontent
                    mps = re.search(mediumPattern, paracontent)
                    if mps and 'artwork_materials' not in detailData.keys():
                        detailData['artwork_materials'] = paracontent
                        detailData['artwork_materials'] = detailData['artwork_materials'].replace("\r", "").replace("\n", "")
                        #print(detailData['artwork_materials'] + " ######")
                    yps = re.search(yearPattern, paracontent)
                    if yps:
                        ypsg = yps.groups()
                        detailData['artwork_start_year'] = ypsg[0]
                        detailData['artwork_end_year'] = ypsg[1]
                    edps = re.search(editionPattern, paracontent)
                    if edps:
                        edpsg = edps.groups()
                        detailData['artwork_edition'] = edpsg[0]
                        numeds = edpsg[1]
                        detailData['artwork_edition'] = "Edition %s/%s"%(detailData['artwork_edition'], numeds)
                    (size, sheetsize, category) = self.getsize(paracontent)
                    size = begindotPattern.sub("", size)
                    size = beginSpacePattern.sub("", size)
                    measureunitPattern = re.compile("([a-zA-Z]{2,})")
                    if size is not None:
                        size = size.replace("by", "x")
                    if 'artwork_size_notes' not in detailData.keys() or detailData['artwork_size_notes'] == "":
                        detailData['artwork_size_notes'] = size
                    #print(detailData['artwork_size_notes'])
                    if "by" in size:
                        sizeparts = size.split("by")
                        detailData['artwork_measurements_height'] = sizeparts[0]
                        detailData['artwork_measurements_height'] = begindotPattern.sub("", detailData['artwork_measurements_height'])
                        if sizeparts.__len__() > 1:
                            mups = re.search(measureunitPattern, sizeparts[1])
                            if mups:
                                detailData['auction_measureunit'] = mups.groups()[0]
                            sizeparts[1] = measureunitPattern.sub("", sizeparts[1])
                            detailData['artwork_measurements_width'] = sizeparts[1]
                        if sizeparts.__len__() > 2:
                            mups = re.search(measureunitPattern, sizeparts[2])
                            if mups:
                                detailData['auction_measureunit'] = mups.groups()[0]
                            sizeparts[2] = measureunitPattern.sub("", sizeparts[2])
                            detailData['artwork_measurements_depth'] = sizeparts[2]
                    if "x" in size:
                        sizeparts = size.split("x")
                        detailData['artwork_measurements_height'] = sizeparts[0]
                        detailData['artwork_measurements_height'] = begindotPattern.sub("", detailData['artwork_measurements_height'])
                        if sizeparts.__len__() > 1:
                            mups = re.search(measureunitPattern, sizeparts[1])
                            if mups:
                                detailData['auction_measureunit'] = mups.groups()[0]
                            sizeparts[1] = measureunitPattern.sub("", sizeparts[1])
                            detailData['artwork_measurements_width'] = sizeparts[1]
                        if sizeparts.__len__() > 2:
                            mups = re.search(measureunitPattern, sizeparts[2])
                            if mups:
                                detailData['auction_measureunit'] = mups.groups()[0]
                            sizeparts[2] = measureunitPattern.sub("", sizeparts[2])
                            detailData['artwork_measurements_depth'] = sizeparts[2]
            #return detailData
        if lotdetailsdiv.__len__() == 0:
            return detailData
        lotdetails = lotdetailsdiv[0].renderContents().decode('utf-8')
        lotdetails = lotdetails.replace("</p><p>", "||")
        lotdetails = self.__class__.htmltagPattern.sub("", lotdetails)
        lotdetailsparts = lotdetails.split("||")
        size = None
        for lotdetailspart in lotdetailsparts:
            lotdetailspart = newlinesPattern.sub("", lotdetailspart)
            lotdetailspart = lotdetailspart.replace('"', "'")
            sps = re.search(signedPattern, lotdetailspart)
            if sps and 'artwork_markings' not in detailData.keys():
                crps = re.search(conditionPattern, lotdetailspart)
                if not crps:
                    detailData['artwork_markings'] = lotdetailspart
                    detailData['artwork_markings'] = detailData['artwork_markings'].replace(",", " ")
                    if self.saleno == "N10669":
                        andPattern = re.compile("\s+and\s*$", re.DOTALL)
                        signedPattern = re.compile("signed", re.IGNORECASE|re.DOTALL)
                        endcommaPattern = re.compile(",\s*$", re.DOTALL)
                        endyearPattern = re.compile("\,\s+\d{4}\s*", re.DOTALL)
                        numberedPattern = re.compile("[and\s\,]{2,4}numbered.*$", re.IGNORECASE|re.DOTALL)
                        inscribedPattern = re.compile("inscrib", re.IGNORECASE)
                        signedParts = re.split(signedPattern, lotdetailspart)
                        detailData['artwork_materials'] = signedParts[0]
                        #print(detailData['artwork_materials'] + "$$$$$$")
                        detailData['artwork_materials'] = andPattern.sub("", detailData['artwork_materials'])
                        mediumparts = re.split(inscribedPattern, detailData['artwork_materials'])
                        if mediumparts.__len__() > 0:
                            detailData['artwork_materials'] = mediumparts[0]
                        publishedparts = detailData['artwork_materials'].split("published")
                        if publishedparts.__len__() > 0:
                            detailData['artwork_materials'] = publishedparts[0]
                        blindstampparts = detailData['artwork_materials'].split("with the blindstamp")
                        if blindstampparts.__len__() > 0:
                            detailData['artwork_materials'] = blindstampparts[0]
                        numberedparts = detailData['artwork_materials'].split("numbered")
                        if numberedparts.__len__() > 0:
                            detailData['artwork_materials'] = numberedparts[0]
                        detailData['artwork_materials'] = endcommaPattern.sub("", detailData['artwork_materials'])
                        detailData['artwork_materials'] = endyearPattern.sub("", detailData['artwork_materials'])
                        detailData['artwork_materials'] = numberedPattern.sub("", detailData['artwork_materials'])
                        if signedParts.__len__() > 1:
                            signature = "Signed" + signedParts[1]
                            sigParts = signature.split(" with ")
                            detailData['artwork_markings'] = sigParts[0]
                            detailData['artwork_markings'] = endcommaPattern.sub("", detailData['artwork_markings'])
                            dotparts = detailData['artwork_markings'].split(".")
                            detailData['artwork_markings'] = dotparts[0]
                            #signatureparts = detailData['artwork_markings'].split(",")
                            #if signatureparts.__len__() > 1:
                            #    detailData['artwork_markings'] = signatureparts[0] + " " + signatureparts[1] 
            sps2 = re.search(signedPattern2, lotdetailspart)
            if sps2 and 'artwork_markings' not in detailData.keys():
                detailData['artwork_markings'] = lotdetailspart
            if 'artwork_markings' in detailData.keys():
                detailData['artwork_markings'] = detailData['artwork_markings'].replace('"', "")
            lotdetailspart = lotdetailspart.replace("&nbsp;", " ")
            edps = re.search(editionPattern, lotdetailspart)
            if edps:
                edpsg = edps.groups()
                detailData['artwork_edition'] = edpsg[0]
                numeds = edpsg[1]
                detailData['artwork_edition'] = "Edition %s/%s"%(detailData['artwork_edition'], numeds)
            if self.saleno == "L21500":
                zps = re.search(sizePattern_sp1, lotdetailspart)
                if zps and not size and size != "":
                    zpsg = zps.groups()
                    size = zpsg[0]
            if self.saleno == "L21164":
                zps = re.search(sizePattern_sp2, lotdetailspart)
                if zps and not size and size != "":
                    zpsg = zps.groups()
                    size = zpsg[0]
                mediumPattern2 = re.compile("(painted)|(madoura\s+stamp)|(polychrome)", re.IGNORECASE|re.DOTALL)
                detailpieces = lotdetailspart.split(",")
                mediumpieces = []
                multispacePattern = re.compile("\s+")
                for pc in detailpieces:
                    pc = multispacePattern.sub(" ", pc)
                    pc = pc.replace("\n", "").replace("\r", "")
                    if re.search(mediumPattern2, pc):
                        mediumpieces.append(pc)
                if 'artwork_materials' not in detailData.keys() and mediumpieces.__len__() > 0:
                    detailData['artwork_materials'] = ", ".join(mediumpieces)
            zpss = re.search(sizePattern_sp1, lotdetailspart)
            if zpss and not size and size != "" and ('artwork_size_notes' not in detailData.keys() or detailData['artwork_size_notes'] == ""):
                zpsg = zpss.groups()
                size = zpsg[0]
            zps = re.search(sizePattern, lotdetailspart)
            if zps and not size and size != "" and ('artwork_size_notes' not in detailData.keys() or detailData['artwork_size_notes'] == ""):
                zpsg = zps.groups()
                size = zpsg[0]
                size = heightPattern.sub("", size)
                size = size.replace("Framed:", "")
            zps4 = re.search(sizePattern4, lotdetailspart)
            if zps4 and not size and size != "" and ('artwork_size_notes' not in detailData.keys() or detailData['artwork_size_notes'] == ""):
                zpsg4 = zps4.groups()
                size = zpsg4[0]
                size = heightPattern.sub("", size)
                size = size.replace("Framed:", "")
            zps2 = re.search(sizePattern2, lotdetailspart)
            if zps2 and not size and size != "" and ('artwork_size_notes' not in detailData.keys() or detailData['artwork_size_notes'] == ""):
                zpsg2 = zps2.groups()
                size = zpsg2[0]
                size = heightPattern.sub("", size)
                size = size.replace("Framed:", "")
            zps3 = re.search(sizePattern3, lotdetailspart)
            if zps3 and not size and size != "" and ('artwork_size_notes' not in detailData.keys() or detailData['artwork_size_notes'] == ""):
                zpsg3 = zps3.groups()
                size = zpsg3[0]
                size = heightPattern.sub("", size)
                size = size.replace("Framed:", "")
            zps5 = re.search(sizePattern5, lotdetailspart)
            if zps5 and not size and size != "" and ('artwork_size_notes' not in detailData.keys() or detailData['artwork_size_notes'] == ""):
                zpsg5 = zps5.groups()
                size = zpsg5[0]
                size = heightPattern.sub("", size)
                size = size.replace("Framed:", "")
            zps6 = re.search(sizePattern6, lotdetailspart)
            if zps6 and not size and size != "" and ('artwork_size_notes' not in detailData.keys() or detailData['artwork_size_notes'] == ""):
                zpsg6 = zps6.groups()
                size = zpsg6[0]
                size = heightPattern.sub("", size)
                size = size.replace("Framed:", "")
            zps7 = re.search(sizePattern7, lotdetailspart)
            if zps7 and not size and size != "" and ('artwork_size_notes' not in detailData.keys() or detailData['artwork_size_notes'] == ""):
                zpsg7 = zps7.groups()
                size = zpsg7[0]
                size = heightPattern.sub("", size)
                size = size.replace("Framed:", "")
            zps8 = re.search(sizePattern8, lotdetailspart)
            if zps8 and not size and size != "" and ('artwork_size_notes' not in detailData.keys() or detailData['artwork_size_notes'] == ""):
                zpsg8 = zps8.groups()
                size = zpsg8[0]
                size = heightPattern.sub("", size)
                size = size.replace("Framed:", "")
            zps9 = re.search(sizePattern9, lotdetailspart)
            if zps9 and not size and size != "" and ('artwork_size_notes' not in detailData.keys() or detailData['artwork_size_notes'] == ""):
                zpsg9 = zps9.groups()
                size = zpsg9[0]
                size = heightPattern.sub("", size)
                size = size.replace("Framed:", "")
            zps9_5 = re.search(sizePattern9_5, lotdetailspart)
            if zps9_5 and not size and size != "" and ('artwork_size_notes' not in detailData.keys() or detailData['artwork_size_notes'] == ""):
                zpsg9_5 = zps9_5.groups()
                size = zpsg9_5[0]
                size = size.replace("Framed:", "")
            zps9_5b = re.search(sizePattern9_5b, lotdetailspart)
            if zps9_5b and not size and size != "" and ('artwork_size_notes' not in detailData.keys() or detailData['artwork_size_notes'] == ""):
                zpsg9_5b = zps9_5b.groups()
                size = zpsg9_5b[0]
            zps9_5a = re.search(sizePattern9_5a, lotdetailspart)
            if zps9_5a and not size and size != "" and ('artwork_size_notes' not in detailData.keys() or detailData['artwork_size_notes'] == ""):
                zpsg9_5a = zps9_5a.groups()
                size = zpsg9_5a[0]
                size = size.replace("Framed:", "")
            zps10 = re.search(sizePattern10, lotdetailspart)
            if zps10 and not size and size != "" and ('artwork_size_notes' not in detailData.keys() or detailData['artwork_size_notes'] == ""):
                zpsg10 = zps10.groups()
                size = zpsg10[0]
                size = heightPattern.sub("", size)
                size = size.replace("Framed:", "")
            zps11b = re.search(sizePattern11b, lotdetailspart)
            if zps11b and not size and size != "" and ('artwork_size_notes' not in detailData.keys() or detailData['artwork_size_notes'] == ""):
                zpsg11b = zps11b.groups()
                size = zpsg11b[0]
                size = heightPattern.sub("", size)
                size = size.replace("Framed:", "")
            zps11c = re.search(sizePattern11c, lotdetailspart)
            if zps11c and not size and size != "" and ('artwork_size_notes' not in detailData.keys() or detailData['artwork_size_notes'] == ""):
                zpsg11c = zps11c.groups()
                size = zpsg11c[0]
                size = heightPattern.sub("", size)
                size = size.replace("Framed:", "")
            zps12 = re.search(sizePattern12, lotdetailspart)
            if zps12 and not size and size != "" and ('artwork_size_notes' not in detailData.keys() or detailData['artwork_size_notes'] == ""):
                zpsg12 = zps12.groups()
                size = zpsg12[0]
                size = heightPattern.sub("", size)
                size = size.replace("Framed:", "")
            zps13 = re.search(sizePattern13, lotdetailspart)
            if zps13 and not size and size != "" and ('artwork_size_notes' not in detailData.keys() or detailData['artwork_size_notes'] == ""):
                zpsg13 = zps13.groups()
                size = zpsg13[0]
                size = heightPattern.sub("", size)
                size = size.replace("Framed:", "")
                #print(detailData['SIZE'])
            if size is not None and size != "" and ('artwork_size_notes' not in detailData.keys() or detailData['artwork_size_notes'] == ""):
                size = size.replace(",",".")
                size = beginSpacePattern.sub("", size)
                size = size.replace("by", "x")
                size = size.replace("; ", "")
                #size = begindotPattern.sub("", size)
                size = beginSpacePattern.sub("", size)
            else:
                pass
            #print(size)
            if type(size) == str:
                size = begindotPattern.sub("", size)
                size = beginSpacePattern.sub("", size)
            measureunitPattern = re.compile("([a-zA-Z]{2,})")
            if 'artwork_size_notes' not in detailData.keys() and size is not None:
                size = size.replace("by", "x")
                detailData['artwork_size_notes'] = size
            if type(size) == str and "by" in size and ('artwork_measurements_height' not in detailData.keys() or detailData['artwork_measurements_height'] == ""):
                sizeparts = size.split("by")
                detailData['artwork_measurements_height'] = sizeparts[0]
                detailData['artwork_measurements_height'] = begindotPattern.sub("", detailData['artwork_measurements_height'])
                if sizeparts.__len__() > 1:
                    mups = re.search(measureunitPattern, sizeparts[1])
                    if mups:
                        detailData['auction_measureunit'] = mups.groups()[0]
                    sizeparts[1] = measureunitPattern.sub("", sizeparts[1])
                    detailData['artwork_measurements_width'] = sizeparts[1]
                if sizeparts.__len__() > 2:
                    mups = re.search(measureunitPattern, sizeparts[2])
                    if mups:
                        detailData['auction_measureunit'] = mups.groups()[0]
                    sizeparts[2] = measureunitPattern.sub("", sizeparts[2])
                    detailData['artwork_measurements_depth'] = sizeparts[2]
            elif type(size) == str and "x" in size and 'artwork_measurements_height' not in detailData.keys():
                sizeparts = size.split("x")
                detailData['artwork_measurements_height'] = sizeparts[0]
                detailData['artwork_measurements_height'] = begindotPattern.sub("", detailData['artwork_measurements_height'])
                if sizeparts.__len__() > 1:
                    mups = re.search(measureunitPattern, sizeparts[1])
                    if mups:
                        detailData['auction_measureunit'] = mups.groups()[0]
                    sizeparts[1] = measureunitPattern.sub("", sizeparts[1])
                    detailData['artwork_measurements_width'] = sizeparts[1]
                if sizeparts.__len__() > 2:
                    mups = re.search(measureunitPattern, sizeparts[2])
                    if mups:
                        detailData['auction_measureunit'] = mups.groups()[0]
                    sizeparts[2] = measureunitPattern.sub("", sizeparts[2])
                    detailData['artwork_measurements_depth'] = sizeparts[2]
            elif type(size) == str and 'artwork_measurements_height' not in detailData.keys():
                detailData['artwork_measurements_height'] = size
                detailData['artwork_measurements_height'] = begindotPattern.sub("", detailData['artwork_measurements_height'])
            mps = re.search(mediumPattern, lotdetailspart)
            if mps and ('artwork_materials' not in detailData.keys() or detailData['artwork_materials'] == ""):
                crps = re.search(conditionPattern, lotdetailspart)
                if not crps:
                    detailData['artwork_materials'] = lotdetailspart
                    sps = re.search(signedPattern, detailData['artwork_materials'])
                    sps2 = re.search(signedPattern2, detailData['artwork_materials'])
                    eps = re.search(editionPattern2, detailData['artwork_materials'])
                    eps3 = re.search(editionPattern3, detailData['artwork_materials'])
                    if sps or sps2 or eps or eps3:
                        mediumparts = detailData['artwork_materials'].split(",")
                        detailData['artwork_materials'] = ""
                        mediumlist = []
                        signaturelist = []
                        emptyspacePattern = re.compile("^\s*$")
                        for medium in mediumparts:
                            if re.search(mediumPattern, medium) and detailData['artwork_materials'] == "":
                                mediumlist.append(medium)
                            if re.search(signedPattern, medium) or re.search(signedPattern2, medium):
                                signaturelist.append(medium)
                            if re.search(editionPattern2, medium) or re.search(editionPattern3, medium):
                                if re.search(editionPattern3, medium) and 'artwork_markings' in detailData.keys() and not re.search(emptyspacePattern, detailData['artwork_markings']):
                                    signaturelist.append(medium)
                                detailData['artwork_edition'] = medium
                                detailData['artwork_edition'] = beginSpacePattern.sub("", detailData['artwork_edition'])
                                #print("Edition Number: %s"%detailData['artwork_edition'])
                        detailData['artwork_materials'] = " ".join(mediumlist)
                        detailData['artwork_materials'] = beginSpacePattern.sub("", detailData['artwork_materials'])
                        detailData['artwork_markings'] = " ".join(signaturelist)
                        detailData['artwork_markings'] = beginSpacePattern.sub("", detailData['artwork_markings'])
                        print("Signature: %s"%detailData['artwork_markings'])
                        print("Medium: %s"%detailData['artwork_materials'])
            yps = re.search(yearPattern, lotdetailspart)
            if yps:
                ypsg = yps.groups()
                detailData['artwork_start_year'] = ypsg[0]
                detailData['artwork_end_year'] = ypsg[1]
            bdys = re.search(birthdeathyearPattern, lotdetailspart)
            if bdys and 'artist_birth' not in detailData.keys():
                bdysg = bdys.groups()
                detailData['artist_birth'] = bdysg[0]
                detailData['artist_death'] = bdysg[1]
            aps = re.search(authenticityPattern, lotdetailspart)
            if aps:
                authenticitytext = aps.groups()[0]
                authenticitytext = beginSpacePattern.sub("", authenticitytext)
                detailData['LETTEROFAUTHENTICITY'] = authenticitytext
            ips = re.search(inscribedPattern, lotdetailspart)
            if ips:
                detailData['INSCRIPTION'] = lotdetailspart
            cps = re.search(conceivedPattern, lotdetailspart)
            if cps:
                cpsg = cps.groups()
                detailData['CONCEPTIONYEARFROM'] = cpsg[0]
                detailData['CONCEPTIONYEARTO'] = cpsg[1]
        lotsoldPattern = re.compile("Lot\s+sold\:\s*([\d\,\.]+)\s+([A-Z]{3})", re.IGNORECASE|re.DOTALL)
        detailspagecontent = self.__class__.htmltagPattern.sub("", detailsPage)
        lsps = re.search(lotsoldPattern, detailspagecontent)
        if lsps:
            detailData['ALTERNATE_SOLD_PRICE'] = lsps.groups()[0] + " " + lsps.groups()[1]
        #finalpricePattern = re.compile("\"finalPrice\"\:(\d{4,})\}")
        #fps = re.findall(finalpricePattern, detailsPage)
        #if fps.__len__() > self.ifctr:
        #    detailData['ALTERNATE_SOLD_PRICE'] = fps[self.ifctr]
        #self.ifctr += 1
        #print(str(detailData['ALTERNATE_SOLD_PRICE']) + " ############# " + str(self.ifctr))
        provenancePattern = re.compile("collapsable\-container\-Provenance", re.DOTALL|re.IGNORECASE)
        exhibitedPattern = re.compile("collapsable\-container\-Exhibited", re.DOTALL|re.IGNORECASE)
        literaturePattern = re.compile("collapsable\-container\-Literature", re.DOTALL|re.IGNORECASE)
        provenancedivs = soup.find_all("div", {'id' : provenancePattern})
        if provenancedivs.__len__() > 0:
            provenancetext = provenancedivs[0].renderContents().decode('utf-8')
            provenancetext = provenancetext.replace('"', "'")
            provenancetext = brPattern.sub("| ", provenancetext)
            provenancetext = self.__class__.htmltagPattern.sub("", provenancetext)
            provenancetext = newlinesPattern.sub("", provenancetext)
            provenancetext = provenancetext.replace("Provenance", "")
            provenancetext = provenancetext.replace("_", "")
            detailData['artwork_provenance'] = provenancetext
        exhibiteddivs = soup.find_all("div", {'id' : exhibitedPattern})
        if exhibiteddivs.__len__() > 0:
            exhibitedtext = exhibiteddivs[0].renderContents().decode('utf-8')
            exhibitedtext = exhibitedtext.replace('"', "'")
            exhibitedtext = brPattern.sub("| ", exhibitedtext)
            exhibitedtext = self.__class__.htmltagPattern.sub("", exhibitedtext)
            exhibitedtext = newlinesPattern.sub("", exhibitedtext)
            exhibitedtext = exhibitedtext.replace("Exhibited", "")
            exhibitedtext = exhibitedtext.replace("_", "")
            detailData['artwork_exhibited'] = exhibitedtext
        literaturedivs = soup.find_all("div", {'id' : literaturePattern})
        if literaturedivs.__len__() > 0:
            literaturetext = literaturedivs[0].renderContents().decode('utf-8')
            literaturetext = literaturetext.replace('"', "'")
            literaturetext = brPattern.sub("| ", literaturetext)
            literaturetext = self.__class__.htmltagPattern.sub("", literaturetext)
            literaturetext = newlinesPattern.sub("", literaturetext)
            literaturetext = literaturetext.replace("Literature", "")
            literaturetext = literaturetext.replace("_", "")
            detailData['artwork_literature'] = literaturetext
        selectedimagelitags = soup.find_all("li", {'class' : 'slide selected'})
        if selectedimagelitags.__len__() > 0:
            mainimgtags = selectedimagelitags[0].findChildren("img", recursive=False)
            if mainimgtags.__len__() > 0:
                mainimgtag = mainimgtags[0]
                defaultimageurl = mainimgtag['src']
                defaultimageurl = defaultimageurl.replace("%3A", ":").replace("%2F", "/")
                #print(defaultimageurl)
                imagename1 = self.getImagenameFromUrl(defaultimageurl)
                imagename1 = str(imagename1)
                imagename1 = imagename1.replace("b'", "").replace("'", "")
                auctiontitle = self.auctiontitle.replace(" ", "_")
                processedAuctionTitle = auctiontitle.replace(" ", "_")
                processedArtistName = artistname.replace(" ", "_")
                processedArtistName = unidecode.unidecode(processedArtistName)
                processedArtworkName = artworkname.replace(" ", "_")
                processedArtworkName = unidecode.unidecode(processedArtworkName)
                auction_number = self.saleno
                sublot_number = ""
                #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + auction_number + "__" + str(lotno) + "__" + sublot_number
                newname1 = self.saleno + "__" + processedArtworkName + "__" + processedArtistName + "__" + str(lotno) + "_a"
                #encryptedFilename = self.encryptFilename(newname1)
                encryptedFilename = newname1
                imagepathparts = defaultimageurl.split("/")
                defimageurl = "/".join(imagepathparts[:-2])
                encryptedFilename = str(encryptedFilename).replace("b'", "")
                encryptedFilename = str(encryptedFilename).replace("'", "")
                detailData['image1_name'] = str(encryptedFilename) + ".jpg"
                detailData['artwork_images1'] = defaultimageurl
                #self.getImage(detailData['artwork_images1'], imagepath, downloadimages)
        addlimglitags = soup.find_all("li", {'class' : 'slide'})
        additionalimageurls = []
        for litag in addlimglitags:
            addlimgtags = litag.findChildren("img", recursive=False)
            if addlimgtags.__len__() > 0:
                addlimgtag = addlimgtags[0]
                addlimgurl = addlimgtag['src']
                additionalimageurls.append(addlimgurl)
        imgctr = 2
        if additionalimageurls.__len__() > 0:
            altimage2 = additionalimageurls[0]
            imagename1 = self.getImagenameFromUrl(altimage2)
            imagename1 = str(imagename1)
            imagename1 = imagename1.replace("b'", "").replace("'", "")
            altimage2parts = altimage2.split("/")
            altimageurl = "/".join(altimage2parts[:-2])
            processedArtistName = artistname.replace(" ", "_")
            processedArtistName = unidecode.unidecode(processedArtistName)
            processedArtworkName = artworkname.replace(" ", "_")
            processedArtworkName = unidecode.unidecode(processedArtworkName)
            sublot_number = ""
            #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + auction_number + "__" + str(lotno) + "__" + sublot_number
            auction_number = self.saleno
            newname1 = auction_number + "__" + processedArtistName + "__" + str(lotno) + "_b"
            #encryptedFilename = self.encryptFilename(newname1)
            encryptedFilename = newname1
            detailData['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
            detailData['artwork_images' + str(imgctr)] = altimage2
            #self.getImage(detailData['artwork_images' + str(imgctr)], imagepath, downloadimages)
            if downloadimages == "1":
                encryptedFilename = str(encryptedFilename) + "-b.jpg"
                self.renameImagefile(imagepath, imagename1, encryptedFilename)
            imgctr += 1
        if additionalimageurls.__len__() > 1:
            altimage3 = additionalimageurls[1]
            imagename1 = self.getImagenameFromUrl(altimage3)
            imagename1 = str(imagename1)
            imagename1 = imagename1.replace("b'", "").replace("'", "")
            altimage3parts = altimage3.split("/")
            altimageurl = "/".join(altimage3parts[:-2])
            processedArtistName = artistname.replace(" ", "_")
            processedArtistName = unidecode.unidecode(processedArtistName)
            processedArtworkName = artworkname.replace(" ", "_")
            processedArtworkName = unidecode.unidecode(processedArtworkName)
            sublot_number = ""
            #newname3 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + auction_number + "__" + str(lotno) + "__" + sublot_number
            auction_number = self.saleno
            newname3 = auction_number + "__" + processedArtistName + "__" + str(lotno) + "_c"
            #encryptedFilename = self.encryptFilename(newname3)
            encryptedFilename = newname3
            detailData['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
            detailData['artwork_images' + str(imgctr)] = altimage3
            #self.getImage(detailData['artwork_images' + str(imgctr)], imagepath, downloadimages)
            if downloadimages == "1":
                encryptedFilename = str(encryptedFilename) + "-b.jpg"
                self.renameImagefile(imagepath, imagename1, encryptedFilename)
            imgctr += 1
        if additionalimageurls.__len__() > 2:
            altimage4 = additionalimageurls[2]
            imagename1 = self.getImagenameFromUrl(altimage4)
            imagename1 = str(imagename1)
            imagename1 = imagename1.replace("b'", "").replace("'", "")
            altimage4parts = altimage4.split("/")
            altimageurl = "/".join(altimage4parts[:-2])
            processedArtistName = artistname.replace(" ", "_")
            processedArtistName = unidecode.unidecode(processedArtistName)
            processedArtworkName = artworkname.replace(" ", "_")
            processedArtworkName = unidecode.unidecode(processedArtworkName)
            sublot_number = ""
            #newname4 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + auction_number + "__" + str(lotno) + "__" + sublot_number
            auction_number = self.saleno
            newname4 = auction_number + "__" + processedArtistName + "__" + str(lotno) + "_d"
            #encryptedFilename = self.encryptFilename(newname4)
            encryptedFilename = newname4
            detailData['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
            detailData['artwork_images' + str(imgctr)] = altimage4
            #self.getImage(detailData['artwork_images' + str(imgctr)], imagepath, downloadimages)
            if downloadimages == "1":
                encryptedFilename = str(encryptedFilename) + "-b.jpg"
                self.renameImagefile(imagepath, imagename1, encryptedFilename)
            imgctr += 1
        if additionalimageurls.__len__() > 3:
            altimage5 = additionalimageurls[3]
            imagename1 = self.getImagenameFromUrl(altimage5)
            imagename1 = str(imagename1)
            imagename1 = imagename1.replace("b'", "").replace("'", "")
            altimage5parts = altimage5.split("/")
            altimageurl = "/".join(altimage5parts[:-2])
            processedArtistName = artistname.replace(" ", "_")
            processedArtistName = unidecode.unidecode(processedArtistName)
            processedArtworkName = artworkname.replace(" ", "_")
            processedArtworkName = unidecode.unidecode(processedArtworkName)
            sublot_number = ""
            #newname5 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + auction_number + "__" + str(lotno) + "__" + sublot_number
            auction_number = self.saleno
            newname5 = auction_number + "__" + processedArtistName + "__" + str(lotno) + "_e"
            #encryptedFilename = self.encryptFilename(newname5)
            encryptedFilename = newname5
            detailData['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
            detailData['artwork_images' + str(imgctr)] = altimage5
            #self.getImage(detailData['artwork_images' + str(imgctr)], imagepath, downloadimages)
            if downloadimages == "1":
                encryptedFilename = str(encryptedFilename) + "-b.jpg"
                self.renameImagefile(imagepath, imagename1, encryptedFilename)
            imgctr += 1
        if 'SIZE' in detailData:
            detailData['SIZE'] = detailData['SIZE'].replace("(", "").replace(")", "")
            detailData['SIZE'] = self.fractionToDecimalSize(detailData['SIZE'])
        if 'SHEETSIZE' in detailData:
            detailData['SHEETSIZE'] = self.fractionToDecimalSize(detailData['SHEETSIZE'])
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
        descriptiondivtags = soup.find_all("div", {'id' : 'LotDetails'})
        if descriptiondivtags.__len__() > 0:
            descriptiontext = descriptiondivtags[0].renderContents().decode('utf-8')
            descriptiontext = self.__class__.htmltagPattern.sub("", descriptiontext)
            descriptiontext = descriptiontext.replace('"', "'")
            descriptiontext = descriptiontext.replace("\n", "").replace("\r", "")
            descriptiontext = descriptiontext.replace("_", "")
            detailData['artwork_description'] = descriptiontext
            detailData['artwork_description'] = detailData['artwork_description'].strip()
            detailData['artwork_description'] = detailData['artwork_description'].replace("Provenance", "<br><strong>Provenance</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("Literature", "<br><strong>Literature</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("Exhibited", "<br><strong>Exhibited</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("Expositions", "<br><strong>Expositions</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("Bibliographie", "<br><strong>Literature</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("Condition Report", "<br><strong>Condition Report</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("Catalogue note:", "<br><strong>Note:</strong><br>")
        if 'artwork_description' in detailData.keys():
            detailData['artwork_description'] = "<strong><br>Description<br></strong>" + detailData['artwork_description']
        return detailData


    def getImage(self, imageUrl, imagepath, downloadimages):
        imageUrlParts = imageUrl.split("/")
        imagefilename = imageUrlParts[-2] + "_" + imageUrlParts[-1]
        imagedir = imageUrlParts[-2]
        headers = {}
        for k in self.httpHeaders.keys():
            headers[k] = self.httpHeaders[k]
        headers['Cookie'] = ""
        headers['Accept-Language'] = "en-GB,en-US;q=0.9,en;q=0.8"
        headers['Accept-Encoding'] = "gzip, deflate"
        headers['Host'] = "sothebys-brightspot.s3.amazonaws.com"
        headers['Connection'] = "keep-alive"
        imageUrlSections = imageUrl.split("?url=")
        imgUrl = imageUrl
        if imageUrlSections.__len__() > 1:
            imgUrl = imageUrlSections[1]
        imgUrl = imgUrl.replace("%3A", ":").replace("%2F", "/")
        if downloadimages == "1":
            pageRequest = urllib.request.Request(imgUrl, headers=headers)
            #pageRequest.set_proxy(self.httpproxylist[3], 'http')
            pageResponse = None
            try:
                pageResponse = self.opener.open(pageRequest)
            except:
                print ("Error %s: %s"%(imgUrl, sys.exc_info()[1].__str__()))
                headers['Host'] = "sothebys-md.brightspotcdn.com"
                pageRequest = urllib.request.Request(imgUrl, headers=headers)
                try:
                    pageResponse = self.opener.open(pageRequest)
                except:
                    pageResponse = None
            try:
                if pageResponse is not None:
                    imageContent = pageResponse.read()
                    ifp = open(imagepath + os.path.sep + imagefilename, "wb")
                    ifp.write(imageContent)
                    ifp.close()
            except:
                print("Error: %s"%sys.exc_info()[1].__str__())
        return imagefilename


    def getInfoFromLotsData(self, datalist, imagepath, downloadimages):
        baseUrl = "https://www.sothebys.com"
        info = []
        chunksize = 4
        counter = 0
        pagecontent = self.currentPageContent
        contentparts = pagecontent.split("\"lotsList\"")
        pricecontent = ""
        if contentparts.__len__() > 1:
            pricecontent = contentparts[1]
        premiumsPattern = re.compile("\"premiums\"\:\{(.*?)\}")
        allpremiums = re.findall(premiumsPattern, pricecontent)
        finalpricePattern = re.compile("\"finalPrice\"\:(\d*)")
        fpctr = 0
        for lotdata in datalist:
            if counter == chunksize:
                counter = 0
                self.opener = urllib.request.build_opener(urllib.request.HTTPHandler(), urllib.request.HTTPSHandler())
            else:
                counter += 1
            data = {}
            data['lot_num'] = lotdata['lotNr']
            lotno = data['lot_num']
            data['auction_house_name'] = "Sotheby's"
            detailUrl = baseUrl + lotdata['slug']
            data['artwork_name'] = lotdata['title']
            data['artwork_name'] = data['artwork_name'].replace('"', "'")
            if self.saleno == "HK1079":
                titleparts = data['artwork_name'].split("|")
                if titleparts.__len__() > 1:
                    data['artwork_name'] = titleparts[1]
            auctionDate = ""
            if 'closingTime' in lotdata.keys():
                auctionDate = lotdata['closingTime']
            if not auctionDate:
                auctionDate = str(lotdata['openDate'])
            auctionDateParts = auctionDate.split("T")
            auctionDateComponents = auctionDateParts[0].split("-")
            if auctionDateComponents.__len__() > 2:
                auctionDateStr = auctionDateComponents[1] + "/" + auctionDateComponents[2] + "/" + auctionDateComponents[0]
                data['auction_start_date'] = auctionDateStr
            currency = str(lotdata['currency'])
            data['price_estimate_min'] = str(lotdata['lowEstimate'])
            data['price_estimate_max'] = str(lotdata['highEstimate'])
            #data['ESTIMATE'] = str(lotdata['estimates']['low']) + " - " + str(lotdata['estimates']['high']) + " " + currency
            try:
                premiums = lotdata['premiums']
                if 'finalPrice' in premiums.keys():
                    if not premiums['finalPrice']:
                        data['price_sold'] = ""
                    else:
                        data['price_sold'] = str(premiums['finalPrice'])
            except:
                pass
            data['price_sold'] = str(lotdata['price']) + " " + currency
            if data['price_sold'] == "None " + currency:
                data['price_sold'] = ""
            if data['price_sold'] == "" and allpremiums.__len__() > fpctr:
                premiumscontent = allpremiums[fpctr]
                #print(premiumscontent)
                finalpricematches = re.search(finalpricePattern, str(premiumscontent))
                if finalpricematches:
                    data['price_sold'] = finalpricematches.groups()[0] + " " + currency
            fpctr += 1
            data['lot_origin_url'] = detailUrl
            data['SALE#'] = self.saleno
            data['artist_name'] = ""
            if lotdata['creators'].__len__() > 0:
                data['artist_name'] = lotdata['creators'][0]
            """
            objects = lotdata['objectSet']['objects']
            for obj in objects:
                if type(obj) == dict and 'object_' in obj.keys():
                    creators = obj['object_']
                    try:
                        data['artist_name'] = creators['creators'][0]['creator']['displayName']
                    except:
                        data['artist_name'] = ""
            """
            print("Getting '%s'..."%detailUrl)
            detailsPageContent = self.getDetailsPage(detailUrl)
            detailData = self.parseDetailPage(detailsPageContent, lotno, imagepath, data['artist_name'], data['artwork_name'], downloadimages)
            for k in detailData.keys():
                data[k] = detailData[k]
            if 'price_sold' in data.keys() and data['price_sold'] == "" and 'ALTERNATE_SOLD_PRICE' in data.keys():
                data['price_sold'] = data['ALTERNATE_SOLD_PRICE']
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
            if 'price_estimate_min' in data.keys():
                data['price_estimate_min'] = data['price_estimate_min'].replace(",", "").replace(" ", "")
            if 'price_estimate_max' in data.keys():
                data['price_estimate_max'] = data['price_estimate_max'].replace(",", "").replace(" ", "")
            if 'price_sold' in data.keys():
                data['price_sold'] = data['price_sold'].replace(",", "").replace(" ", "")
            if 'auction_start_date' in data.keys():
                mondict = {'01' : 'Jan', '02' : 'Feb', '03' : 'Mar', '04' : 'Apr', '05' : 'May', '06' : 'Jun', '07' : 'Jul', '08' : 'Aug', '09' : 'Sep', '10' : 'Oct', '11' : 'Nov', '12' : 'Dec' }
                dateparts = data['auction_start_date'].split("/")
                yy, mmm, dd = "", "", ""
                if dateparts.__len__() > 2:
                    yyyy = dateparts[2]
                    if yyyy.__len__() == 4:
                        yy = yyyy[2:]
                    else:
                        yy = yyyy
                    mm = dateparts[1]
                    if int(mm) > 12:
                        mmm = mondict[dateparts[0]]
                        dd = dateparts[1]
                    else:
                        mmm = mondict[mm]
                        dd = dateparts[0]
                    startdate = dd + "-" + mmm + "-" + yy
                else:
                    startdate = data['auction_start_date']
                data['auction_start_date'] = startdate
            if re.search(re.compile("[a-zA-Z]+"), data['price_sold']):
                data['price_sold'] = re.compile("[a-zA-Z]+").sub("", data['price_sold'])
            print(data['price_sold'])
            data['auction_name'] = self.auctiontitle
            data['auction_location'] = self.auctionlocation
            data['auction_num'] = self.saleno
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
    pageurl = "http://216.137.189.57:8080/scrapers/finish/?scrapername=Sothebys&auctionnumber=%s&auctionurl=%s&scrapertype=2"%(auctionno, urllib.parse.quote(auctionurl))
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
    sothebys = SothebysBot(auctionurl, auctionnumber)
    fp = open(csvpath, "w")
    fieldnames = ['auction_house_name', 'auction_location', 'auction_num', 'auction_start_date', 'auction_end_date', 'auction_name', 'lot_num', 'sublot_num', 'price_kind', 'price_estimate_min', 'price_estimate_max', 'price_sold', 'artist_name', 'artist_birth', 'artist_death', 'artist_nationality', 'artwork_name', 'artwork_year_identifier', 'artwork_start_year', 'artwork_end_year', 'artwork_materials', 'artwork_category', 'artwork_markings', 'artwork_edition', 'artwork_description', 'artwork_measurements_height', 'artwork_measurements_width', 'artwork_measurements_depth', 'artwork_size_notes', 'auction_measureunit', 'artwork_condition_in', 'artwork_provenance', 'artwork_exhibited', 'artwork_literature', 'artwork_images1', 'artwork_images2', 'artwork_images3', 'artwork_images4', 'artwork_images5', 'image1_name', 'image2_name', 'image3_name', 'image4_name', 'image5_name', 'lot_origin_url']
    fieldsstr = ",".join(fieldnames)
    fp.write(fieldsstr + "\n")
    lotsdata = sothebys.getLotsFromPage()
    pagectr = 1
    while True:
        info = sothebys.getInfoFromLotsData(lotsdata, imagepath, downloadimages)
        lotctr = 0 
        for d in info:
            lotctr += 1
            for f in fieldnames:
                if f in d and d[f] is not None:
                    try:
                        fp.write('"' + str(d[f]) + '",')
                    except:
                        pass
                else:
                    fp.write('"",')
            fp.write("\n")
        postdata = {"query":"","filters":"auctionId:%s AND objectTypes:\"All\""%sothebys.aid,"facetFilters":[["withdrawn:false"]],"hitsPerPage":48,"page":pagectr,"facets":["*"],"numericFilters":[]}
        postdatastr = json.dumps(postdata)
        #postdatastr = urllib.parse.urlencode(postdata)
        requestUrl = "https://kar1ueupjd-dsn.algolia.net/1/indexes/prod_lots/query?x-algolia-agent=Algolia%20for%20JavaScript%20(4.8.3)%3B%20Browser"
        httpheaders = {}
        httpheaders['content-type'] = "application/x-www-form-urlencoded"
        httpheaders['Accept'] = "*/*"
        httpheaders['Connection'] = "keep-alive"
        httpheaders['Cache-Control'] = "no-cache"
        httpheaders['Host'] = "kar1ueupjd-dsn.algolia.net"
        httpheaders['Origin'] = "https://www.sothebys.com"
        httpheaders['Pragma'] = "no-cache"
        httpheaders['Referer'] = "https://www.sothebys.com/"
        httpheaders['Sec-Fetch-Dest'] = "empty"
        httpheaders['Sec-Fetch-Mode'] = "cors"
        httpheaders['Sec-Fetch-Site'] = "cross-site"
        httpheaders['User-Agent'] = "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:97.0) Gecko/20100101 Firefox/97.0"
        httpheaders['x-algolia-api-key'] = "LvmVnUg1l5tD5x40KydzKJAOBTXjESPn"
        httpheaders['x-algolia-api-key'] = sothebys.algolia_api_key
        httpheaders['x-algolia-application-id'] = "KAR1UEUPJD"
        httpheaders['Content-Length'] = postdatastr.__len__()
        nextpagerequest = urllib.request.Request(requestUrl, postdatastr.encode("utf-8"), headers=httpheaders)
        try:
            pageResponse = sothebys.opener.open(nextpagerequest)
        except:
            print("Could't get next page - Error: %s"%sys.exc_info()[1].__str__())
            break
        pagecontent = sothebys.__class__._decodeGzippedContent(pageResponse.read())
        jsondata = json.loads(pagecontent)
        lotsdata = jsondata['hits']
        if lotsdata.__len__() == 0:
            break
        pagectr += 1
    fp.close()
    #updatestatus(auctionnumber, auctionurl)
    

# Example: python sothebys.py https://www.sothebys.com/en/buy/auction/2021/tableaux-dessins-sculptures-1300-1900 PF2109 /home/supmit/work/artwork/sothebys_PF2109.csv /home/supmit/work/artwork/images/sothebys/PF2109 0 0
# supmit

