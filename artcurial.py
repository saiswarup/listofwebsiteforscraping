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


class ArtcurialBot(object):
    
    startUrl=r"https://www.artcurial.com/fr/vente-a3907-un-printemps-marocain"
    htmltagPattern = re.compile("\<\/?[^\<\>]*\/?\>", re.DOTALL)
    pathEndingWithSlashPattern = re.compile(r"\/$")

    htmlEntitiesDict = {'&nbsp;' : ' ', '&#160;' : ' ', '&amp;' : '&', '&#38;' : '&', '&lt;' : '<', '&#60;' : '<', '&gt;' : '>', '&#62;' : '>', '&apos;' : '\'', '&#39;' : '\'', '&quot;' : '"', '&#34;' : '"'}

    """
    Initialization would include fetching the login page of the email service.
    """
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
        #self.requestUrl = self.__class__.startUrl
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
        #mondict3 = {'jan.' : '01', 'fév.' : '02', 'mar.' : '03', 'avr.' : '04', 'mai.' : '05', 'jui.' : '06', 'jul.' : '07', 'aoû.' : '08', 'sep.' : '09', 'oct.' : '10', 'nov.' : '11', 'déc.' : '12' }
        mondict3 = {'Jan.' : '01', 'Feb.' : '02', 'Mar.' : '03', 'Apr.' : '04', 'May.' : '05', 'Jun.' : '06', 'Jul.' : '07', 'Aug.' : '08', 'Sep.' : '09', 'Oct.' : '10', 'Nov.' : '11', 'Dec.' : '12' }
        datestrcomponents = datestr.split(" ")
        if not datestr:
            return ""
        dd = datestrcomponents[0]
        mm = '01'
        datestrcomponents[1] = datestrcomponents[1].capitalize()
        if datestrcomponents[1] in mondict.keys():
            mm = mondict[datestrcomponents[1]]
        else:
            mm = mondict3[datestrcomponents[1]]
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
        baseUrl = "https://www.artcurial.com"
        pageContent = self.currentPageContent
        multiplewhitespacePattern = re.compile("\s+")
        soup = BeautifulSoup(pageContent, features="html.parser")
        alltitletags = soup.find_all("title")
        if alltitletags.__len__() > 0:
            title = alltitletags[0].renderContents().decode('utf-8')
            titleparts = title.split("|")
            if titleparts.__len__() > 0:
                self.auctiontitle = titleparts[0]
        lotnoPattern = re.compile("^\d+$", re.DOTALL)
        allMosaicDivs = soup.find_all("div", {'id' : lotnoPattern})
        datespans = soup.find_all("span", {'class' : 'sale-name'})
        if datespans.__len__() > 0:
            datecontent = datespans[0].renderContents().decode('utf-8')
            contentPattern = re.compile("\w+\s+Sale\s+\-\s+([\d\w\s]+)", re.IGNORECASE|re.DOTALL)
            cps = re.search(contentPattern, datecontent)
            if cps:
                self.auctiondate = cps.groups()[0]
        if not self.auctiondate or self.auctiondate == "":
            tabletags = soup.find_all("table", {'class' : 'table-desktop-only'})
            datePattern = re.compile("(\d{1,2}\s+\w+\s+\d{4})")
            if tabletags.__len__() > 0:
                tablecontent = tabletags[0].renderContents().decode('utf-8')
                dps = re.search(datePattern, tablecontent)
                if dps:
                    self.auctiondate = dps.groups()[0]
                locationptags = tabletags[0].find_all("p")
                if locationptags.__len__() > 0:
                    self.auctionlocation = locationptags[0].renderContents().decode('utf-8')
                    self.auctionlocation = self.auctionlocation.replace("\n", "").replace("\r", "")
                    self.auctionlocation = multiplewhitespacePattern.sub(" ", self.auctionlocation)
        return allMosaicDivs
        

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
        os.rename(oldfilename, newfilename)


    def getImagenameFromUrl(self, imageUrl):
        urlparts = imageUrl.split("/")
        imagefilepart = urlparts[-1]
        imagefilenameparts = imagefilepart.split("?")
        imagefilename = imagefilenameparts[0]
        return imagefilename


    def parseDetailPage(self, detailsPage, lotno, imagepath, artistname, artworkname, downloadimages):
        baseUrl = "https://www.artcurial.com"
        detailData = {}
        soup = BeautifulSoup(detailsPage, features="html.parser")
        productvisualsPattern = re.compile("product-visuals__description", re.DOTALL)
        productvisualsdivs = soup.find_all("div", {'class' : productvisualsPattern})
        if productvisualsdivs.__len__() == 0:
            return detailData
        productcontent = productvisualsdivs[0].renderContents().decode('utf-8')
        productcontentparts = re.split("<br\s?\/>", productcontent)
        provenancePattern = re.compile("provenance", re.IGNORECASE|re.DOTALL)
        literaturePattern = re.compile("bibliographie", re.IGNORECASE|re.DOTALL)
        signedPattern = re.compile("signed", re.IGNORECASE|re.DOTALL)
        nonenglishsignedPattern = re.compile("(annoté)|(\s+signéd?\s+)|(Signée)", re.IGNORECASE|re.DOTALL)
        mediumPattern = re.compile("commentaire", re.IGNORECASE|re.DOTALL)
        inscriptionPattern1 = re.compile("titled", re.IGNORECASE|re.DOTALL)
        inscriptionPattern2 = re.compile("inscribed", re.IGNORECASE|re.DOTALL)
        sizePattern = re.compile("hauteur\s*:\s*([\d,]*)\s*[&;nbsp]*\s*largeur\s*:\s*([\d,]*)\s*[&;nbsp]*\s*[profondeur\s:&nbsp;]*([\d,]*)\s*[&;nbsp]*\s*([\w]{2})", re.IGNORECASE|re.DOTALL)
        sizePattern2 = re.compile("h:\s([\d,]*)[^:]+w:\s+([\d,]*)[^cmin]+([\w]{2})", re.IGNORECASE|re.DOTALL)
        sizePattern3 = re.compile("h:\s([\d,]+)[^:]+w:\s+([\d,]*)[^:]+d?:?\s*([\d,]*)\s?([\w]{2})", re.IGNORECASE|re.DOTALL)
        sizePattern4 = re.compile("h:\s([\d,]+)\s+([\w]{2})", re.IGNORECASE|re.DOTALL)
        materialPattern = re.compile("(glass)|(paper)|(wood)|(brass)|(canvas)|(iron)|(wax)|(oak)|(panel)|(chalk)|(\s+ink)|(copper)|(oil\s+)|(bronze)|(plaster)", re.IGNORECASE|re.DOTALL)
        nonenglishmediumPattern = re.compile("(crayon)|(encre)|(plume)|(plume\s+et\s+encre)|(papier)|(pastel)|(craie)|(gouachée)|(aquarelle)|(lithographique)|(plomb)|(huile)|(cuivre)|(toile)|(bronze)|(Plâtre)|(décor)|(sablée)|(sculpté)|(redoré)|(chêne)|(gouache)|(gravures)|(crayon)|(d'encre\s+de\s+chine)", re.IGNORECASE|re.DOTALL)
        estimatePattern = re.compile("Estimation\s+([\d,\s\.]+)\s*\-\s*([\d,\s\.]+)\s+€", re.IGNORECASE|re.DOTALL)
        leadingspacePattern = re.compile("^\s+", re.DOTALL)
        colonPattern = re.compile("\:", re.DOTALL)
        matcatdict_en = {}
        matcatdict_fr = {}
        #with open("docs/fineart_materials.csv", newline='') as mapfile:
        with open("/Users/saiswarupsahu/freelanceprojectchetan/docs/fineart_materials.csv", newline='') as mapfile:
            mapreader = csv.reader(mapfile, delimiter=",", quotechar='"')
            for maprow in mapreader:
                matcatdict_en[maprow[1]] = maprow[3]
                matcatdict_fr[maprow[2]] = maprow[3]
        mapfile.close()
        contentctr = 0
        for productcontentpart in productcontentparts:
            productcontentpart = productcontentpart.replace('"', "'")
            pvs = re.search(provenancePattern, productcontentpart)
            if pvs:
                detailData['artwork_provenance'] = productcontentpart
                detailData['artwork_provenance'] = detailData['artwork_provenance'].replace("PROVENANCE", "")
                detailData['artwork_provenance'] = provenancePattern.sub("", detailData['artwork_provenance'])
                detailData['artwork_provenance'] = detailData['artwork_provenance'].replace(":", "")
                detailData['artwork_provenance'] = leadingspacePattern.sub("", detailData['artwork_provenance'])
                if productcontentparts.__len__() > contentctr + 1:
                    probableprovenanceinfo = productcontentparts[contentctr + 1]
                    cps = re.search(colonPattern, probableprovenanceinfo)
                    stps = re.search(re.compile("strong", re.DOTALL), probableprovenanceinfo)
                    if not cps and not stps and probableprovenanceinfo != "":
                        detailData['artwork_provenance'] += ", " + probableprovenanceinfo
                detailData['artwork_provenance'] = detailData['artwork_provenance'].replace('"', "")
            lts = re.search(literaturePattern, productcontentpart)
            if lts:
                detailData['artwork_literature'] = productcontentpart
                detailData['artwork_literature'] = detailData['artwork_literature'].replace("Bibliographie", "")
                detailData['artwork_literature'] = detailData['artwork_literature'].replace('"', "'")
                detailData['artwork_literature'] = literaturePattern.sub("", detailData['artwork_literature'])
                detailData['artwork_literature'] = detailData['artwork_literature'].replace(":", "")
                detailData['artwork_literature'] = leadingspacePattern.sub("", detailData['artwork_literature'])
            sps = re.search(signedPattern, productcontentpart)
            if sps and ('artwork_markings' not in detailData.keys() or detailData['artwork_markings'] == ""):
                detailData['artwork_markings'] = productcontentpart
                detailData['artwork_markings'] = leadingspacePattern.sub("", detailData['artwork_markings'])
            nesps = re.search(nonenglishsignedPattern, productcontentpart)
            if nesps: # If there is non-english content for signature values, it is preferred.
                detailData['artwork_markings'] = productcontentpart
                detailData['artwork_markings'] = leadingspacePattern.sub("", detailData['artwork_markings'])
            #mps = re.search(mediumPattern, productcontentpart)
            #if 'artwork_materials' in detailData.keys() and mps:
            #    detailData['artwork_materials'] = productcontentpart
            #    detailData['artwork_materials'] = detailData['artwork_materials'].replace("Commentaire", "")
            #    detailData['artwork_materials'] = detailData['artwork_materials'].replace(":", "")
            #    detailData['artwork_materials'] = leadingspacePattern.sub("", detailData['artwork_materials'])
            mts = re.search(materialPattern, productcontentpart)
            if mts and ('artwork_materials' not in detailData.keys() or detailData['artwork_materials'] == ""):
                detailData['artwork_materials'] = productcontentpart
                detailData['artwork_materials'] = detailData['artwork_materials'].replace("Commentaire", "")
                detailData['artwork_materials'] = detailData['artwork_materials'].replace(":", "")
                detailData['artwork_materials'] = leadingspacePattern.sub("", detailData['artwork_materials'])
            nemps = re.search(nonenglishmediumPattern, productcontentpart)
            if nemps and (('artwork_materials' in detailData.keys() and not re.search(nonenglishmediumPattern, detailData['artwork_materials'])) or 'artwork_materials' not in detailData.keys()): # If there is non-english content for medium, it gets preference over english values for medium. However, if artwork_materials already contains non-english content, then we skip the operation.
                detailData['artwork_materials'] = productcontentpart
                detailData['artwork_materials'] = detailData['artwork_materials'].replace("Commentaire", "")
                detailData['artwork_materials'] = detailData['artwork_materials'].replace(":", " ")
                detailData['artwork_materials'] = leadingspacePattern.sub("", detailData['artwork_materials'])
            if 'artwork_materials' in detailData.keys():
                detailData['artwork_materials'] = detailData['artwork_materials'].replace("'", "")
                detailData['artwork_materials'] = detailData['artwork_materials'].replace('"', "")
                detailData['artwork_materials'] = self.__class__.htmltagPattern.sub(" ", detailData['artwork_materials'])
                detailData['artwork_materials'] = detailData['artwork_materials'].replace("France; ", "") # For auction number 4096
                mediumparts = detailData['artwork_materials'].split(";")
                for mediumpart in mediumparts:
                    mtsnew = re.search(materialPattern, mediumpart)
                    if mtsnew:
                        detailData['artwork_materials'] = mediumpart
                detailData['artwork_materials'] = detailData['artwork_materials'].replace(",", ";")
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
            szp = re.search(sizePattern, productcontentpart)
            if szp:
                szpg = szp.groups()
                height = szpg[0]
                length = szpg[1]
                width = szpg[2]
                unit = szpg[3]
                detailData['artwork_size_notes'] = height + " x " + length
                detailData['artwork_measurements_height'] = height
                if width:
                    detailData['artwork_size_notes'] += " x " + width
                    detailData['artwork_measurements_width'] = width
                detailData['artwork_size_notes'] += " " + unit
                detailData['auction_measureunit'] = unit
            szp2 = re.search(sizePattern2, productcontentpart)
            if 'artwork_size_notes' not in detailData.keys() and szp2:
                szpg2 = szp2.groups()
                height = szpg2[0]
                length = szpg2[1]
                unit = szpg2[2]
                height = height.replace(",", ".")
                length = length.replace(",", ".")
                detailData['artwork_size_notes'] = height + " x " + length
                detailData['artwork_measurements_height'] = height
                detailData['artwork_measurements_width'] = length
                detailData['artwork_size_notes'] += " " + unit
                detailData['auction_measureunit'] = unit
                #print("Size = " + detailData['artwork_size_notes'])
            szp3 = re.search(sizePattern3, productcontentpart)
            if 'artwork_size_notes' not in detailData.keys() and szp3:
                szpg3 = szp3.groups()
                height = szpg3[0]
                length = szpg3[1]
                breadth = ""
                if szpg3[2] != "":
                    breadth = szpg3[2]
                unit = szpg3[3]
                height = height.replace(",", ".")
                length = length.replace(",", ".")
                breadth = unitbreadth.replace(",", ".")
                detailData['artwork_size_notes'] = height + " x " + length
                detailData['artwork_measurements_height'] = height
                if szpg3[2] != "":
                    detailData['artwork_size_notes'] += "x" + breadth
                    detailData['artwork_measurements_width'] = breadth
                #print("Size = " + detailData['artwork_size_notes'])
                detailData['artwork_size_notes'] += " " + unit
                detailData['auction_measureunit'] = unit
            contentpart = productcontentpart.replace("&nbsp;", " ")
            szp4 = re.search(sizePattern4, contentpart)
            if 'artwork_size_notes' not in detailData.keys() and szp4:
                szpg4 = szp4.groups()
                height = szpg4[0]
                unit = szpg4[1]
                height = height.replace(",", ".")
                detailData['artwork_size_notes'] = height + " " + unit
                detailData['artwork_measurements_height'] = height
                detailData['auction_measureunit'] = unit
            ips1 = re.search(inscriptionPattern1, productcontentpart)
            if ips1:
                isps = re.search(signedPattern, productcontentpart)
                if not isps:
                    detailData['artwork_markings'] = productcontentpart
                    detailData['artwork_markings'] = leadingspacePattern.sub("", detailData['artwork_markings'])
            ips2 = re.search(inscriptionPattern2, productcontentpart)
            if ips2:
                isps = re.search(signedPattern, productcontentpart)
                if not isps:
                    detailData['artwork_markings'] = productcontentpart
                    detailData['artwork_markings'] = leadingspacePattern.sub("", detailData['artwork_markings'])
            contentctr += 1
            eps = re.search(estimatePattern, productcontentpart)
            if eps and 'price_estimate_min' not in detailData.keys():
                high = str(eps.groups()[1])
                low = str(eps.groups()[0])
                high = high.replace(" ", "")
                low = low.replace(" ", "")
                detailData['price_estimate_min'] = low
                detailData['price_estimate_max'] = high
        auctiondetailsdivs = soup.find_all("div", {'class' : 'product-accordion__text smooth'})
        auctiondetailscontent = auctiondetailsdivs[0].renderContents().decode('utf-8')
        auctiondetailsparts = re.split("<br\s?\/>", auctiondetailscontent)
        saleno = auctiondetailsparts[0]
        spacePattern = re.compile("\s+", re.DOTALL)
        saleno = spacePattern.sub("", saleno)
        saleno = saleno.replace("Vente:", "")
        saleno = saleno.replace("Sale:", "")
        detailData['auction_num'] = saleno
        if auctiondetailsparts.__len__() > 2:
            auctiondate = auctiondetailsparts[2]
            auctiondate = spacePattern.sub("", auctiondate)
            auctiondate = auctiondate.replace("Date:", "")
            auctiondatePattern = re.compile("(\d+)([a-z\.]+)(\d{4})")
            ads = re.search(auctiondatePattern, auctiondate)
            if ads:
                adsg = ads.groups()
                date = adsg[0]
                mon = adsg[1]
                year = adsg[2]
                auctiondate = " ".join([date, mon, year])
                detailData['auction_start_date'] = self.__class__.formatDate(auctiondate)
        productvisualsdiv = soup.find_all("div", {'class' : 'product-visuals'})
        productvisualscontent = productvisualsdiv[0].renderContents().decode('utf-8')
        s = BeautifulSoup(productvisualscontent, features="html.parser")
        prodimgtag = s.find_all("img")[0]
        prodimg = baseUrl + prodimgtag['src']
        prodimgparts = prodimg.split("styles/840_width/public/")
        defaultimageurl = prodimg
        if prodimgparts.__len__() > 1:
            defaultimageurl = prodimgparts[0] + prodimgparts[1]
        #print("Image URL: " + defaultimageurl)
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
        visualPattern = re.compile("product\-visuals__description")
        visualdescdivtags = soup.find_all("div", {'class' : visualPattern})
        if visualdescdivtags.__len__() > 0:
            visualcontent = visualdescdivtags[0].renderContents().decode('utf-8')
            nationalityPattern = re.compile("\-\s*(\w+)\s+")
            nps = re.search(nationalityPattern, visualcontent)
            if nps:
                detailData['artist_nationality'] = nps.groups()[0]
        descriptiondivPattern = re.compile("description\-tablet\-portrait\-down")
        descdivtags = soup.find_all("div", {'class' : descriptiondivPattern})
        if descdivtags.__len__() > 0:
            descdivcontents = descdivtags[0].renderContents().decode('utf-8')
            descdivcontents = descdivcontents.replace("\n", "").replace("\r", "")
            detailData['artwork_description'] = descdivcontents
            detailData['artwork_description'] = detailData['artwork_description'].strip()
            detailData['artwork_description'] = self.__class__.htmltagPattern.sub("", detailData['artwork_description'])
            detailData['artwork_description'] = detailData['artwork_description'].replace("\n", " ")
            detailData['artwork_description'] = detailData['artwork_description'].replace("\r", " ")
            detailData['artwork_description'] = detailData['artwork_description'].replace('"', "'")
            detailData['artwork_description'] = detailData['artwork_description'].replace("Provenance", "<br><strong>Provenance</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("Literature", "<br><strong>Literature</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("Exhibited", "<br><strong>Exhibited</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("Expositions", "<br><strong>Expositions</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("Bibliographie", "<br><strong>Literature</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("Condition Report", "<br><strong>Condition Report</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("Notes:", "<br><strong>Notes:</strong><br>")
            detailData['artwork_description'] = "<strong><br>Description<br></strong>" + detailData['artwork_description']
        return detailData


    def getInfoFromLotsData(self, htmlList, imagepath, downloadimages):
        baseUrl = "https://www.artcurial.com"
        info = []
        endSpacePattern = re.compile("\s+$", re.DOTALL)
        for htmldiv in htmlList:
            data = {}
            artistname, artworkname = "", ""
            htmlContent = htmldiv.renderContents().decode('utf-8')
            s = BeautifulSoup(htmlContent, features="html.parser")
            allanchors = s.find_all("a")
            htmlanchor = allanchors[0]
            detailUrl = baseUrl + htmlanchor['href']
            imgtag = s.find_all("img")
            if imgtag.__len__() > 0:
                hdImg = baseUrl + imgtag[0]['data-hd']
                sdImg = baseUrl + imgtag[0]['data-sd']
                alternateImageUrls = [sdImg, hdImg]
            else:
                alternateImageUrls = []
            lotnoP = s.find_all("p", {'class' : 'mosaic__item-number'})
            lotno = lotnoP[0].renderContents().decode('utf-8')
            lotno = self.__class__.htmltagPattern.sub("", lotno)
            data['lot_num'] = lotno
            iteminfo = s.find_all("h2", {'class' : 'mosaic__item-name'})
            itemcontents = iteminfo[0].renderContents().decode('utf-8')
            itemNameParts = itemcontents.split("</strong>")
            artistname = itemNameParts[0]
            if itemNameParts.__len__() > 1:
                birthdeathdateParts = itemNameParts[1].split("<br/>")
                birthdeathdates = birthdeathdateParts[0]
                if birthdeathdateParts.__len__() > 1:
                    itemnamedate = birthdeathdateParts[1]
                else:
                    itemnamedate = ""
            else:
                itemnamedate = ""
            artistname = self.__class__.htmltagPattern.sub("", artistname)
            data['artist_name'] = artistname
            birthdeathdates = self.__class__.htmltagPattern.sub("", birthdeathdates)
            bdparts = birthdeathdates.split("-")
            birthdate = bdparts[0]
            nonnumPattern = re.compile("[^\d]+", re.DOTALL)
            birthdate = nonnumPattern.sub("", birthdate)
            data['artist_birth'] = birthdate
            if bdparts.__len__() > 1:
                deathdate = bdparts[1]
                deathdate = re.compile("[^\d]+", re.DOTALL).sub("", deathdate)
                data['artist_death'] = deathdate
            itemnamedate = self.__class__.htmltagPattern.sub("", itemnamedate)
            itemnamedate = endSpacePattern.sub("", itemnamedate)
            itemnamedateParts = itemnamedate.split(",")
            itemdate = itemnamedateParts[-1]
            datePattern = re.compile("(\d{4}[\/\-]?\d{0,4})", re.DOTALL)
            dps = re.search(datePattern, itemdate)
            endcommaPattern = re.compile("\,\s*$", re.DOTALL)
            if dps and 'artwork_name' not in data.keys():
                itemname = ",".join(itemnamedateParts[:-1])
                if itemname == "":
                    itemname = itemnamedateParts[0]
                itemname = itemname.replace("circa", "")
                itemnameparts = itemname.split("-")
                itemname = itemnameparts[0]
                itemname = endcommaPattern.sub("", itemname)
                itemname = endSpacePattern.sub("", itemname)
                itemname = decodeHtmlEntities(itemname)
                data['artwork_name'] = itemname.replace('"', "'")
                artworkname = data['artwork_name']
                itemdateParts = re.split("[\/\-]", itemdate)
                yearfrom = nonnumPattern.sub("", itemdateParts[0])
                data['artwork_start_year'] = yearfrom
                if itemdateParts.__len__() > 1:
                    yearto = itemdateParts[1]
                    yearto = nonnumPattern.sub("", yearto)
                    data['artwork_end_year'] = yearto
            else:
                itemname = ", ".join(itemnamedateParts)
                itemname = endcommaPattern.sub("", itemname)
                itemname = endSpacePattern.sub("", itemname)
                itemname = decodeHtmlEntities(itemname)
                data['artwork_name'] = itemname.replace('"', "'")
                artworkname = data['artwork_name']
            if 'artwork_name' not in data.keys() or data['artwork_name'] == "":
                tparts = itemnamedateParts[0].split("-")
                data['artwork_name'] = tparts[0].replace('"', "'")
                data['artwork_name'] = endSpacePattern.sub("", data['artwork_name'])
                artworkname = data['artwork_name']
            if 'artwork_name' in data.keys():
                titlePattern = re.compile('"([a-zA-Z]+)"', re.DOTALL)
                tps = re.search(titlePattern, data['artwork_name'])
                if tps:
                    data['artwork_name'] = tps.groups()[0]
                data['artwork_name'] = data['artwork_name'].replace('"', "'")
                data['artwork_name'] = data['artwork_name'].replace(',', ";")
                artworkname = data['artwork_name']
            data['lot_origin_url'] = detailUrl
            estimatetags = s.find_all("p", {'class' : 'mosaic__item-price'})
            estimateinfo = estimatetags[0].renderContents().decode('utf-8')
            estimateinfo = self.__class__.htmltagPattern.sub("", estimateinfo)
            estimatePattern = re.compile("([\d\s]*)\s+([A-Z]{3})\s+\-\s+([\d\s]*)\s+([A-Z]{3})", re.IGNORECASE|re.DOTALL)
            eps = re.search(estimatePattern, estimateinfo)
            if eps:
                epsg = eps.groups()
                estimatefrom = epsg[0].replace(" ", ",")
                estimateto = epsg[2].replace(" ", ",")
                estimatecurrency = epsg[1]
                data['price_estimate_min'] = estimatefrom
                data['price_estimate_max'] = estimateto
            if 'price_estimate_min' not in data.keys() or data['price_estimate_min'] == "":
                estimatePattern2 = re.compile("([^\[]+)", re.DOTALL)
                eps2 = re.search(estimatePattern2, estimateinfo)
                if eps2:
                    epsg2 = eps2.groups()
                    estimate = epsg2[0]
                    estimate = estimate.replace("€", "")
                    estimate = estimate + " EUR"
                    soldPattern = re.compile("Sold\s+([\d,\.]+\s+[A-Z]{3})")
                    sps = re.search(soldPattern, estimate)
                    if sps:
                        data['price_sold'] = sps.groups()[0]
                    else:
                        estimateparts = estimate.split(" - ")
                        data['price_estimate_min'] = estimateparts[0]
                        if estimateparts.__len__() > 1:
                            data['price_estimate_max'] = estimateparts[1]
                    #print(data['price_estimate_min'])
            data['auction_house_name'] = 'Artcurial'
            print("Getting '%s'..."%detailUrl)
            detailsPageContent = self.getDetailsPage(detailUrl)
            detailData = self.parseDetailPage(detailsPageContent, lotno, imagepath, artistname, artworkname, downloadimages)
            for k in detailData.keys():
                data[k] = detailData[k]
            withdrawnPattern = re.compile("withdrawn", re.IGNORECASE|re.DOTALL)
            data['price_kind'] = "unknown"
            if ('price_sold' in data.keys() and re.search(withdrawnPattern, data['price_sold'])) or ('price_estimate_max' in data.keys() and  re.search(withdrawnPattern, data['price_estimate_max'])):
                data['price_kind'] = "withdrawn"
            elif 'price_sold' in data.keys() and 'price_sold' in data.keys() and data['price_sold'] != "":
                data['price_kind'] = "price realized"
            elif 'price_estimate_max' in data.keys() and data['price_estimate_max'] != "":
                data['price_kind'] = "estimate"
            else:
                pass
            imgctr = 2
            if alternateImageUrls.__len__() > 0:
                altimage2 = alternateImageUrls[0]
                altimage2parts = altimage2.split("/")
                altimageurl = "/".join(altimage2parts[:-2])
                data['image' + str(imgctr) + '_name'] = self.getImagenameFromUrl(altimage2)
                processedAuctionTitle = self.auctiontitle.replace(" ", "_")
                processedArtistName = artistname.replace(" ", "_")
                processedArtistName = unidecode.unidecode(processedArtistName)
                processedArtworkName = artworkname.replace(" ", "_")
                sublot_number = ""
                #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + self.saleno + "__" + lotno + "__" + sublot_number
                newname1 = self.saleno + "__" + processedArtistName + "__" + lotno + "_b"
                #encryptedFilename = self.encryptFilename(newname1)
                encryptedFilename = newname1
                data['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
                data['artwork_images' + str(imgctr)] = altimage2
                imgctr += 1
            if alternateImageUrls.__len__() > 1:
                altimage3 = alternateImageUrls[1]
                altimage3parts = altimage3.split("/")
                altimageurl = "/".join(altimage3parts[:-2])
                data['image' + str(imgctr) + '_name'] = self.getImagenameFromUrl(altimage3)
                processedAuctionTitle = self.auctiontitle.replace(" ", "_")
                processedArtistName = artistname.replace(" ", "_")
                processedArtistName = unidecode.unidecode(processedArtistName)
                processedArtworkName = artworkname.replace(" ", "_")
                sublot_number = ""
                #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + self.saleno + "__" + lotno + "__" + sublot_number
                newname1 = self.saleno + "__" + processedArtistName + "__" + lotno + "_c"
                #encryptedFilename = self.encryptFilename(newname1)
                encryptedFilename = newname1
                data['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
                data['artwork_images' + str(imgctr)] = altimage3
                imgctr += 1
            if alternateImageUrls.__len__() > 2:
                altimage4 = alternateImageUrls[2]
                altimage4parts = altimage4.split("/")
                altimageurl = "/".join(altimage4parts[:-2])
                data['image' + str(imgctr) + '_name'] = self.getImagenameFromUrl(altimage4)
                processedAuctionTitle = self.auctiontitle.replace(" ", "_")
                processedArtistName = artistname.replace(" ", "_")
                processedArtistName = unidecode.unidecode(processedArtistName)
                processedArtworkName = artworkname.replace(" ", "_")
                sublot_number = ""
                #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + self.saleno + "__" + lotno + "__" + sublot_number
                newname1 = self.saleno + "__" + processedArtistName + "__" + lotno + "_d"
                #encryptedFilename = self.encryptFilename(newname1)
                encryptedFilename = newname1
                data['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
                data['artwork_images' + str(imgctr)] = altimage4
                imgctr += 1
            if alternateImageUrls.__len__() > 3:
                altimage5 = alternateImageUrls[3]
                altimage5parts = altimage5.split("/")
                altimageurl = "/".join(altimage5parts[:-2])
                data['image' + str(imgctr) + '_name'] = self.getImagenameFromUrl(altimage5)
                processedAuctionTitle = self.auctiontitle.replace(" ", "_")
                processedArtistName = artistname.replace(" ", "_")
                processedArtistName = unidecode.unidecode(processedArtistName)
                processedArtworkName = artworkname.replace(" ", "_")
                sublot_number = ""
                #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + self.saleno + "__" + lotno + "__" + sublot_number
                newname1 = self.saleno + "__" + processedArtistName + "__" + lotno + "_e"
                #encryptedFilename = self.encryptFilename(newname1)
                encryptedFilename = newname1
                data['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
                data['artwork_images' + str(imgctr)] = altimage5
            if 'price_sold' not in data.keys() or data['price_sold'] == "":
                data['price_sold'] = "0"
            #data['auction_start_date'] = self.__class__.formatDate(self.auctiondate)
            data['auction_start_date'] = self.auctiondate
            if 'price_estimate_min' in data.keys():
                data['price_estimate_min'] = data['price_estimate_min'].replace(",", "").replace(" ", "")
            if 'price_estimate_max' in data.keys():
                data['price_estimate_max'] = data['price_estimate_max'].replace(",", "").replace(" ", "")
            if 'price_sold' in data.keys():
                data['price_sold'] = data['price_sold'].replace(",", "").replace(" ", "")
            if 'auction_start_date' in data.keys():
                mondict = {'01' : 'Jan', '02' : 'Feb', '03' : 'Mar', '04' : 'Apr', '05' : 'May', '06' : 'Jun', '07' : 'Jul', '08' : 'Aug', '09' : 'Sep', '10' : 'Oct', '11' : 'Nov', '12' : 'Dec' }
                dateparts = data['auction_start_date'].split(" ")
                yy, mmm, dd = "", "", ""
                if dateparts.__len__() > 2:
                    yyyy = dateparts[2]
                    if yyyy.__len__() == 4:
                        yy = yyyy[2:]
                    else:
                        yy = yyyy
                    mmm = dateparts[1]
                    dd = dateparts[0]
                    startdate = dd + "-" + mmm + "-" + yy
                else:
                    startdate = data['auction_start_date']
                data['auction_start_date'] = startdate
            data['auction_location'] = self.auctionlocation
            data['auction_start_date'] = data['auction_start_date'].replace("\n", " ").replace("\r\n", " ")
            data['auction_name'] = self.auctiontitle
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
    pageurl = "http://216.137.189.57:8080/scrapers/finish/?scrapername=Artcurial&auctionnumber=%s&auctionurl=%s&scrapertype=2"%(auctionno, urllib.parse.quote(auctionurl))
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
    artcurial = ArtcurialBot(auctionurl, auctionnumber)
    fp = open(csvpath, "w")
    fieldnames = ['auction_house_name', 'auction_location', 'auction_num', 'auction_start_date', 'auction_end_date', 'auction_name', 'lot_num', 'sublot_num', 'price_kind', 'price_estimate_min', 'price_estimate_max', 'price_sold', 'artist_name', 'artist_birth', 'artist_death', 'artist_nationality', 'artwork_name', 'artwork_year_identifier', 'artwork_start_year', 'artwork_end_year', 'artwork_materials', 'artwork_category', 'artwork_markings', 'artwork_edition', 'artwork_description', 'artwork_measurements_height', 'artwork_measurements_width', 'artwork_measurements_depth', 'artwork_size_notes', 'auction_measureunit', 'artwork_condition_in', 'artwork_provenance', 'artwork_exhibited', 'artwork_literature', 'artwork_images1', 'artwork_images2', 'artwork_images3', 'artwork_images4', 'artwork_images5', 'image1_name', 'image2_name', 'image3_name', 'image4_name', 'image5_name', 'lot_origin_url']
    fieldsstr = ",".join(fieldnames)
    fp.write(fieldsstr + "\n")
    lotsdata = artcurial.getLotsFromPage()
    info = artcurial.getInfoFromLotsData(lotsdata, imagepath, downloadimages)
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

# Example: python artcurial.py  https://www.artcurial.com/en/sale-3891-comic-strips   3891  /Users/saiswarupsahu/freelanceprojectchetan/artcurial_3891.csv  /Users/saiswarupsahu/freelanceprojectchetan/Aguttes/Image/121480   0  0 
# supmit

