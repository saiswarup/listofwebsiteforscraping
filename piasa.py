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


class PiasaBot(object):
    
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
        urlPattern = re.compile("https://www.piasa.fr/en/auctions/([^#]+)#lots-list")
        ups = re.search(urlPattern, auctionurl)
        if ups:
            slug = ups.groups()[0]
        else:
            print("Improper auction URL value")
            exit()
        targeturl = "https://api.piasa.fr/api/auctions/%s?with[]=lots.product.media&with[]=lots.product.translation&with[]=lots.product.lots&with[]=lots.product.artist&with[]=lots.product.bids.user&with[]=online_bids&with[]=media&with[]=employees&with[]=free_catalog&with[]=paid_catalog"%slug
        self.requestUrl = targeturl
        parsedUrl = urlparse(self.requestUrl)
        self.baseUrl = parsedUrl.scheme + "://" + parsedUrl.netloc
        #print(self.requestUrl)
        headers = {}
        for k in self.httpHeaders.keys():
            headers[k] = self.httpHeaders[k]
        headers['Accept'] = "application/json, text/plain, */*"
        headers['authorization'] = "null"
        headers['Content-Type'] = "application/json;charset=utf-8"
        headers['Host'] = "api.piasa.fr"
        headers['Origin'] = "https://www.piasa.fr"
        headers['Referer'] = "https://www.piasa.fr/"
        headers['sec-fetch-dest'] = "empty"
        headers['sec-fetch-mode'] = "cors"
        headers['sec-fetch-site'] = "same-site"
        headers['X-Requested-With'] = "XMLHttpRequest"
        headers['cache-control'] = "no-cache"
        headers['pragma'] = "no-cache"
        headers['lang'] = "en"
        self.pageRequest = urllib.request.Request(self.requestUrl, headers=headers)
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
        jsondata = json.loads(pageContent)
        self.auctiontitle = jsondata['translation']['title']
        self.saleno = jsondata['translation']['auction_id']
        try:
            lotblocks = jsondata['lots']
        except:
            lotblocks = []
        return lotblocks
        

    def getDetailsPage(self, detailUrl):
        headers = {}
        for k in self.httpHeaders.keys():
            headers[k] = self.httpHeaders[k]
        headers['Accept'] = "application/json, text/plain, */*"
        headers['authorization'] = "null"
        headers['Content-Type'] = "application/json;charset=utf-8"
        headers['Host'] = "api.piasa.fr"
        headers['Origin'] = "https://www.piasa.fr"
        headers['Referer'] = "https://www.piasa.fr/"
        headers['sec-fetch-dest'] = "empty"
        headers['sec-fetch-mode'] = "cors"
        headers['sec-fetch-site'] = "same-site"
        headers['X-Requested-With'] = "XMLHttpRequest"
        headers['cache-control'] = "no-cache"
        headers['pragma'] = "no-cache"
        headers['lang'] = "en"
        self.requestUrl = detailUrl
        self.pageRequest = urllib.request.Request(self.requestUrl, headers=headers)
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


    def parseDetailPage(self, detailsPage, lotno, imagepath, downloadimages):
        baseUrl = "https://www.piasa.fr"
        detailData = {}
        jsondata = json.loads(detailsPage)
        print(jsondata)
        
        mediumPattern = re.compile("(gold)|(silver)|(brass)|(bronze)|(wood)|(porcelain)|(stone)|(marble)|(metal)|(steel)|(iron)|(glass)|(plexiglas)|(chromogenic)|(paper)|(canvas)|(masonite)|(newsprint)|(silkscreen)|(parchment)|(linen)|(inkjet)|(ink\s+jet)|(pigment)|(\stin\s)|(photogravure)|(^oil\s+)|(\s+panel\s+)|(terracotta)|(ivory)|(\s+oak\s+)|(^oak\s+)|(\s+oak$)|(alabaster)|(\s+ink\s+)|(pencil)|(albumen)|(oil\s+)|(\s+oil)|(panel)|(acrylic)", re.DOTALL|re.IGNORECASE)
        nonenglishmediumPattern = re.compile("(crayon)|(encre)|(plume)|(plume\s+et\s+encre)|(papier)|(pastel)|(craie)|(gouachée)|(aquarelle)|(lithographique)|(plomb)|(huile)|(cuivre)|(toile)|(bronze)|(Plâtre)|(en\s+terre\s+de\s+faïence)", re.IGNORECASE|re.DOTALL)
        signedPattern = re.compile("signed\s+", re.IGNORECASE)
        editionPattern = re.compile("edition", re.IGNORECASE)
        sizePattern = re.compile("([\d\.,]+\s*x\s*[\d\.,]+\s*x?\s*[\d\.,]*\s+[a-zA-Z]{2});", re.IGNORECASE)
        sizePattern2 = re.compile("([\d,\.]+\s*x\s*[\d,\.]+\s*[a-zA-Z]{2})", re.IGNORECASE)
        sizePattern3 = re.compile("([\d,]+\s*cm)", re.IGNORECASE)
        sizePattern4 = re.compile("([\d,]+\s*mm)", re.IGNORECASE)
        provenancePattern = re.compile("provenance\s*:", re.IGNORECASE)
        exhibitedPattern = re.compile("exhibited\s*:", re.IGNORECASE)
        literaturePattern = re.compile("literature\s*:", re.IGNORECASE)
        conditionPattern = re.compile("condition\s+report", re.IGNORECASE)
        signaturePattern = re.compile("sign", re.IGNORECASE)
        yearPattern = re.compile("(\d{4})\s*\-?\s*(\d{0,4})", re.DOTALL)
        brPattern = re.compile("<br\s*\/?>", re.IGNORECASE)
        measureunitPattern = re.compile("([a-zA-Z]{2})")
        multispacePattern = re.compile("\s+")
        beginspacePattern = re.compile("^\s+")
        endcommaPattern = re.compile(",\s*$")
        endhyphenPattern = re.compile("\s*\-\s*$")
        matcatdict_en = {}
        matcatdict_fr = {}
        #with open("docs/fineart_materials.csv", newline='') as mapfile:
        with open("/Users/saiswarupsahu/freelanceprojectchetan/docs/fineart_materials.csv", newline='') as mapfile:
            mapreader = csv.reader(mapfile, delimiter=",", quotechar='"')
            for maprow in mapreader:
                matcatdict_en[maprow[1]] = maprow[3]
                matcatdict_fr[maprow[2]] = maprow[3]
        mapfile.close()
        description = jsondata['translation']['description']
        namecontent = jsondata['translation']['name']
        # François Bouillon (born in 1944) Application didactique du principe mele, 1985
        # Jean-Pierre Bertrand (1937-2016) Bleu-rouge (Diptyque), 1983
        namePattern1 = re.compile("^([^\(]+)\s+\((\d{4})\s*\-\s*(\d{4})\)\s+([^\d]+)\s+([\d]{4})")
        namePattern2 = re.compile("^([^\(]+)\s+\(.*(\d{4})\)\s+([^\d]+)\s+(\d{4})")
        namePattern3 = re.compile("^([^\(]+)\s+\((\d{4})\s*\-\s*(\d{4})\)\s+([^\d]+)\s*$")
        namePattern4 = re.compile("^([^\(]+)\s+\(.*(\d{4})\)\s+([^\d]+)\s*")
        namePattern5 = re.compile("^([^\(]+)\s+\((\d{4})\s*\-\s*(\d{4})\)\s*$")
        namePattern6 = re.compile("^([^\(]+)\s[(].*?[)]\s+([^\d]+)\s+(\d{4})")
        namePattern7 = re.compile("^([^\(]+)\s+\((\d{4})\s*\-\s*(\d{4}).*?[)]\s+([^\d]+)\s*$")
        namePattern8 = re.compile("^([^\(]+)\s.*[(].*?[)]\s+([^\d]+)")
        nps1 = re.search(namePattern1, namecontent)
        nps2 = re.search(namePattern2, namecontent)
        nps3 = re.search(namePattern3, namecontent)
        nps4 = re.search(namePattern4, namecontent)
        nps5 = re.search(namePattern5, namecontent)
        nps6 = re.search(namePattern6, namecontent)
        nps7 = re.search(namePattern7, namecontent)
        nps8 = re.search(namePattern8, namecontent)

        if nps1:
            detailData['artist_name'] = nps1.groups()[0]
            detailData['artist_birth'] = nps1.groups()[1]
            detailData['artist_death'] = nps1.groups()[2]
            detailData['artwork_name'] = nps1.groups()[3]
            detailData['artwork_start_year'] = nps1.groups()[4]
        elif nps2:
            detailData['artist_name'] = nps2.groups()[0]
            detailData['artist_birth'] = nps2.groups()[1]
            detailData['artwork_name'] = nps2.groups()[2]
            detailData['artwork_start_year'] = nps2.groups()[3]
        elif nps3:
            detailData['artist_name'] = nps3.groups()[0]
            detailData['artist_birth'] = nps3.groups()[1]
            detailData['artist_death'] = nps3.groups()[2]
            detailData['artwork_name'] = nps3.groups()[3]
        elif nps4:
            detailData['artist_name'] = nps4.groups()[0]
            detailData['artist_birth'] = nps4.groups()[1]
            detailData['artwork_name'] = nps4.groups()[2]
        elif nps5:
            detailData['artist_name'] = nps5.groups()[0]
            detailData['artist_birth'] = nps5.groups()[1]
            detailData['artist_death'] = nps5.groups()[2]
            detailData['artwork_name'] = ""
        elif nps6:
            detailData['artist_name'] = nps6.groups()[0]
            detailData['artwork_name'] = nps6.groups()[1]
            detailData['artwork_start_year'] = nps6.groups()[2]
        elif nps7:
            detailData['artist_name'] = nps7.groups()[0]
            detailData['artist_birth'] = nps7.groups()[1]
            detailData['artist_death'] = nps7.groups()[2]
            detailData['artwork_name'] = nps7.groups()[3]
        elif nps8:
            detailData['artist_name'] = nps8.groups()[0]
            detailData['artwork_name'] = nps8.groups()[1]
     
        else:
            detailData['artist_name'] = ""
            detailData['artist_birth'] = ""
            detailData['artist_death'] = ""
            detailData['artwork_name'] = ""
            detailData['artwork_start_year'] = ""
            detailData['artwork_name'] = ""

        detailData['artwork_name'] = endcommaPattern.sub("", detailData['artwork_name'])
        detailData['artwork_name'] = endhyphenPattern.sub("", detailData['artwork_name'])
       
        detailData['artwork_description'] = description
        detailData['artwork_description'] = detailData['artwork_description'].strip()
        detailData['artwork_description'] = self.__class__.htmltagPattern.sub("", detailData['artwork_description'])
        detailData['artwork_description'] = detailData['artwork_description'].replace("\n", " ")
        detailData['artwork_description'] = detailData['artwork_description'].replace("\r", " ")
        detailData['artwork_description'] = detailData['artwork_description'].replace('"', "'")
        detailData['artwork_description'] = detailData['artwork_description'].replace("Provenance", "<br><strong>Provenance</strong><br>")
        detailData['artwork_description'] = detailData['artwork_description'].replace("Literature", "<br><strong>Literature</strong><br>")
        detailData['artwork_description'] = detailData['artwork_description'].replace("Exhibited", "<br><strong>Exhibited</strong><br>")
        detailData['artwork_description'] = detailData['artwork_description'].replace("Exposition", "<br><strong>Expositions</strong><br>")
        detailData['artwork_description'] = detailData['artwork_description'].replace("Bibliographie", "<br><strong>Literature</strong><br>")
        detailData['artwork_description'] = detailData['artwork_description'].replace("Condition report", "<br><strong>Condition Report</strong><br>")
        detailData['artwork_description'] = detailData['artwork_description'].replace("Notes:", "<br><strong>Notes:</strong><br>")
        detailData['artwork_description'] = "<strong><br>Description<br></strong>" + detailData['artwork_description']
        detailData['artwork_description'] = detailData['artwork_description'].replace('"', "'")
        descparts = re.split(brPattern, description)
        dctr = 0
        for descpart in descparts:
            mps = re.search(mediumPattern, descpart)
            zps = re.search(sizePattern, descpart)
            zps2 = re.search(sizePattern2, descpart)
            zps3 = re.search(sizePattern3, descpart)
            zps4 = re.search(sizePattern4, descpart)
            sps = re.search(signaturePattern, descpart)
            if mps and 'artwork_materials' not in detailData.keys():
                detailData['artwork_materials'] = descpart
                detailData['artwork_materials'] = detailData['artwork_materials'].replace('"', "'")
                detailData['artwork_materials'] = detailData['artwork_materials'].replace(';', " ")
            if zps:
                detailData['artwork_size_notes'] = zps.groups()[0]
            elif zps2:
                detailData['artwork_size_notes'] = zps2.groups()[0]
            elif zps3:
                detailData['artwork_size_notes'] = zps3.groups()[0]
            elif zps4:
                detailData['artwork_size_notes'] = zps4.groups()[0]
            if sps and 'artwork_markings' not in detailData.keys():
                detailData['artwork_markings'] = descpart
                detailData['artwork_markings'] = detailData['artwork_markings'].replace('"', "'")
                detailData['artwork_markings'] = detailData['artwork_markings'].replace(";", " ")
                detailData['artwork_markings'] = beginspacePattern.sub("", detailData['artwork_markings'])
            pps = re.search(provenancePattern, descpart)
            if pps:
                d = dctr
                provenance = ""
                while d < descparts.__len__():
                    if ":" not in descparts[d]: # If we get something like 'Condition report : ' or 'Literature : ', then we will 'break' out.
                        provenance += " " + descparts[d]
                    else:
                        break
                    d += 1
                dctr = d
                detailData['artwork_provenance'] = provenance
            lps = re.search(literaturePattern, descpart)
            if lps:
                d = dctr
                literature = ""
                while d < descparts.__len__():
                    if ":" not in descparts[d]: # If we get something like 'Condition report : ' or 'Literature : ', then we will 'break' out.
                        literature += " " + descparts[d]
                    else:
                        break
                    d += 1
                dctr = d
                detailData['artwork_literature'] = literature
            xps = re.search(exhibitedPattern, descpart)
            if xps:
                d = dctr
                exhibited = ""
                while d < descparts.__len__():
                    if ":" not in descparts[d]: # If we get something like 'Condition report : ' or 'Literature : ', then we will 'break' out.
                        exhibited += " " + descparts[d]
                    else:
                        break
                    d += 1
                dctr = d
                detailData['artwork_exhibited'] = exhibited
            cps = re.search(conditionPattern, descpart)
            if cps:
                d = dctr
                condition = ""
                while d < descparts.__len__():
                    if ":" not in descparts[d]: # If we get something like 'Condition report : ' or 'Literature : ', then we will 'break' out.
                        condition += " " + descparts[d]
                    else:
                        break
                    d += 1
                dctr = d
                detailData['artwork_condition_in'] = condition
            dctr += 1
        if 'artwork_material' not in detailData.keys():
            detailData['artwork_material'] = ""
        if 'artwork_size_notes' not in detailData.keys():
            detailData['artwork_size_notes'] = ""
        else:
            detailData['artwork_size_notes'] = detailData['artwork_size_notes'].lower()
            sizeparts = detailData['artwork_size_notes'].split("x")
            detailData['artwork_measurements_height'] = sizeparts[0]
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
        medialist = jsondata['media']
        defaultimageurl = ""
        alternateimgurls = []
        if medialist.__len__() > 0:
            defaultimageurl = baseUrl + medialist[0]['link']
        for imgobj in medialist[1:]:
            alternateimgurls.append(baseUrl + imgobj['link'])
        imagename1 = self.getImagenameFromUrl(defaultimageurl)
        imagename1 = str(imagename1)
        imagename1 = imagename1.replace("b'", "").replace("'", "")
        auctiontitle = self.auctiontitle.replace(" ", "_")
        processedAuctionTitle = auctiontitle.replace(" ", "_")
        processedArtistName = detailData['artist_name'].replace(" ", "_")
        processedArtistName = unidecode.unidecode(processedArtistName)
        processedArtworkName = detailData['artwork_name'].replace(" ", "_")
        sublot_number = ""
        #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + str(self.saleno) + "__" + lotno + "__" + sublot_number
        newname1 = str(self.saleno) + "__" + processedArtistName + "__" + str(lotno) + "_a"
        #encryptedFilename = self.encryptFilename(newname1)
        encryptedFilename = newname1
        imagepathparts = defaultimageurl.split("/")
        defimageurl = "/".join(imagepathparts[:-2])
        encryptedFilename = str(encryptedFilename).replace("b'", "")
        encryptedFilename = str(encryptedFilename).replace("'", "")
        detailData['image1_name'] = str(encryptedFilename) + ".jpg"
        detailData['artwork_images1'] = defaultimageurl
        artistname = detailData['artist_name']
        artworkname = detailData['artwork_name']
        imgctr = 2
        if alternateimgurls.__len__() > 0:
            altimage2 = alternateimgurls[0]
            altimage2parts = altimage2.split("/")
            altimageurl = "/".join(altimage2parts[:-2])
            processedArtistName = artistname.replace(" ", "_")
            processedArtistName = unidecode.unidecode(processedArtistName)
            processedArtworkName = artworkname.replace(" ", "_")
            sublot_number = ""
            #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + str(self.saleno) + "__" + lotno + "__" + sublot_number
            newname1 = str(self.saleno) + "__" + processedArtistName + "__" + str(lotno) + "_b"
            #encryptedFilename = self.encryptFilename(newname1)
            encryptedFilename = newname1
            detailData['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
            detailData['artwork_images' + str(imgctr)] = altimage2
            imgctr += 1
        if alternateimgurls.__len__() > 1:
            altimage2 = alternateimgurls[1]
            altimage2parts = altimage2.split("/")
            altimageurl = "/".join(altimage2parts[:-2])
            processedArtistName = artistname.replace(" ", "_")
            processedArtistName = unidecode.unidecode(processedArtistName)
            processedArtworkName = artworkname.replace(" ", "_")
            sublot_number = ""
            #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + str(self.saleno) + "__" + lotno + "__" + sublot_number
            newname1 = str(self.saleno) + "__" + processedArtistName + "__" + str(lotno) + "_c"
            #encryptedFilename = self.encryptFilename(newname1)
            encryptedFilename = newname1
            detailData['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
            detailData['artwork_images' + str(imgctr)] = altimage2
            imgctr += 1
        if alternateimgurls.__len__() > 2:
            altimage2 = alternateimgurls[2]
            altimage2parts = altimage2.split("/")
            altimageurl = "/".join(altimage2parts[:-2])
            processedArtistName = artistname.replace(" ", "_")
            processedArtistName = unidecode.unidecode(processedArtistName)
            processedArtworkName = artworkname.replace(" ", "_")
            sublot_number = ""
            #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + str(self.saleno) + "__" + lotno + "__" + sublot_number
            newname1 = str(self.saleno) + "__" + processedArtistName + "__" + str(lotno) + "_d"
            #encryptedFilename = self.encryptFilename(newname1)
            encryptedFilename = newname1
            detailData['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
            detailData['artwork_images' + str(imgctr)] = altimage2
            imgctr += 1
        if alternateimgurls.__len__() > 3:
            altimage2 = alternateimgurls[3]
            altimage2parts = altimage2.split("/")
            altimageurl = "/".join(altimage2parts[:-2])
            processedArtistName = artistname.replace(" ", "_")
            processedArtistName = unidecode.unidecode(processedArtistName)
            processedArtworkName = artworkname.replace(" ", "_")
            sublot_number = ""
            #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + str(self.saleno) + "__" + lotno + "__" + sublot_number
            newname1 = str(self.saleno) + "__" + processedArtistName + "__" + str(lotno) + "_e"
            #encryptedFilename = self.encryptFilename(newname1)
            encryptedFilename = newname1
            detailData['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
            detailData['artwork_images' + str(imgctr)] = altimage2
        detailData['auction_house_name'] = "Piasa"
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


    def getInfoFromLotsData(self, lotblocks, imagepath, downloadimages):
        baseUrl = "https://www.piasa.fr"
        info = []
        endSpacePattern = re.compile("\s+$", re.DOTALL)
        beginspacePattern = re.compile("^\s+")
        emptyspacePattern = re.compile("^\s*$")
        for lotinfo in lotblocks:
            data = {}
            data['auction_num'] = self.saleno
            detailUrl = "https://api.piasa.fr/api/products/%s?with[]=lots.auction.categories.translation&with[]=lots.auction.translation&with[]=lots.auction.employees&with[]=bids&with[]=condition_media"%lotinfo['product']['slug']
            lotno = str(lotinfo['lot_number'])
            data['price_estimate_min'] = str(lotinfo['product']['min_estimation'])
            data['price_estimate_max'] = str(lotinfo['product']['max_estimation'])
            data['price_sold'] = str(lotinfo['product']['price'])
            dateparts = str(lotinfo['auction_date']).split(" ")
            if dateparts.__len__() > 0:
                data['auction_start_date'] = dateparts[0]
            else:
                data['auction_start_date'] = ""
            data['lot_num'] = lotno
            data['lot_origin_url'] = "https://www.piasa.fr/en/products/%s"%lotinfo['product']['slug']
            print("Getting '%s'..."%data['lot_origin_url'])
            if detailUrl == "":
                break
            detailsPageContent = self.getDetailsPage(detailUrl)
            detailData = self.parseDetailPage(detailsPageContent, lotno, imagepath, downloadimages)
            for k in detailData.keys():
                data[k] = detailData[k]
            if 'price_sold' not in data.keys() or data['price_sold'] == "None":
                data['price_sold'] = "0"
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
            data['auction_name'] = self.auctiontitle
            data['auction_location'] = "Paris"
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
    pageurl = "http://216.137.189.57:8080/scrapers/finish/?scrapername=Piasa&auctionnumber=%s&auctionurl=%s&scrapertype=2"%(auctionno, urllib.parse.quote(auctionurl))
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
    auctionurl = auctionurl + "&pg=10"
    piasa = PiasaBot(auctionurl, auctionnumber)
    fp = open(csvpath, "w")
    fieldnames = ['auction_house_name', 'auction_location', 'auction_num', 'auction_start_date', 'auction_end_date', 'auction_name', 'lot_num', 'sublot_num', 'price_kind', 'price_estimate_min', 'price_estimate_max', 'price_sold', 'artist_name', 'artist_birth', 'artist_death', 'artist_nationality', 'artwork_name', 'artwork_year_identifier', 'artwork_start_year', 'artwork_end_year', 'artwork_materials', 'artwork_category', 'artwork_markings', 'artwork_edition', 'artwork_description', 'artwork_measurements_height', 'artwork_measurements_width', 'artwork_measurements_depth', 'artwork_size_notes', 'auction_measureunit', 'artwork_condition_in', 'artwork_provenance', 'artwork_exhibited', 'artwork_literature', 'artwork_images1', 'artwork_images2', 'artwork_images3', 'artwork_images4', 'artwork_images5', 'image1_name', 'image2_name', 'image3_name', 'image4_name', 'image5_name', 'lot_origin_url']
    fieldsstr = ",".join(fieldnames)
    fp.write(fieldsstr + "\n")
    pagectr = 1
    soup = BeautifulSoup(piasa.currentPageContent, features="html.parser")

    while True:
        lotsdata = piasa.getLotsFromPage()
        print(lotsdata.__len__())
        if lotsdata.__len__() == 0:
            break
        info = piasa.getInfoFromLotsData(lotsdata, imagepath, downloadimages)
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
        nextpageanchors = soup.find_all("a", {'id' : 'pagination-nav-%s'%str(pagectr)})
        if nextpageanchors.__len__() > 0:
            nextpageUrl = piasa.baseUrl[:-1] + nextpageanchors[0]['href']
            piasa.pageRequest = urllib.request.Request(nextpageUrl, headers=piasa.httpHeaders)
            try:
                piasa.pageResponse = piasa.opener.open(piasa.pageRequest)
            except:
                print("Couldn't find the page %s"%str(pagectr))
                break
            piasa.currentPageContent = piasa.__class__._decodeGzippedContent(piasa.getPageContent())
        else:
            break
    fp.close()
    updatestatus(auctionnumber, auctionurl)

# Example: python piasa.py "https://www.piasa.fr/en/auctions/scandinavian-design-11-22#lots-list" A6 /Users/saiswarupsahu/freelanceprojectchetan/piasa_A6.csv /Users/saiswarupsahu/freelanceprojectchetan/1-5TNCV9 0 0












