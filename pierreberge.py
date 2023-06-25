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


class PierreBergeBot(object):
    
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
        allmetatags = soup.find_all("meta", {'property' : 'og:title'})
        housePattern = re.compile("(.*)\s+\-\s+Pierre\s+Bergé\s+\&\s+Associés", re.IGNORECASE)
        if allmetatags.__len__() > 0:
            titlecontents = allmetatags[0]['content']
            hps = re.search(housePattern, titlecontents)
            if hps:
                beginspacePattern = re.compile("^\s+")
                endspacePattern = re.compile("\s+$")
                title = hps.groups()[0]
                title = beginspacePattern.sub("", title)
                title = endspacePattern.sub("", title)
                self.auctiontitle = title
        datedivtags = soup.find_all("div", {'class' : 'date_vente'})
        datePattern = re.compile("(\d{1,2}\s+[^\d\s]+\s+\d{4})")
        if datedivtags.__len__() > 0:
            datecontents = datedivtags[0].renderContents().decode('utf-8')
            dps = re.search(datePattern, datecontents)
            if dps:
                self.auctiondate = dps.groups()[0]
        lotblocks = soup.find_all("div", {'class' : 'product-desc'})
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


    def parseDetailPage(self, detailsPage, lotno, imagepath, downloadimages):
        baseUrl = "https://www.pba-auctions.com"
        detailData = {}
        soup = BeautifulSoup(detailsPage, features="html.parser")
        mediumPattern = re.compile("(gold)|(silver)|(brass)|(bronze)|(wood)|(porcelain)|(stone)|(marble)|(metal)|(steel)|(iron)|(glass)|(plexiglas)|(chromogenic)|(paper)|(canvas)|(masonite)|(newsprint)|(silkscreen)|(parchment)|(linen)|(inkjet)|(ink\s+jet)|(pigment)|(\stin\s)|(photogravure)|(^oil\s+)|(\s+panel\s+)|(terracotta)|(ivory)|(\s+oak\s+)|(^oak\s+)|(\s+oak$)|(alabaster)|(polycarbonate\s+honeycomb)|(c\-print)|(acrylic)|(burlap)|(colou?r\s+photograph)|(gouache)|(terra\s+cotta)|(terracotta)|(on\s+panel)|(lithograph)|(on\s+board)|(sculpture)|(ceramic)|(photographic\s+printing)|(poster)|(dye\-transfer)|(cibachrome)", re.DOTALL|re.IGNORECASE)
        nonenglishmediumPattern = re.compile("(crayon)|(encre)|(plume)|(plume\s+et\s+encre)|(papier)|(pastel)|(craie)|(gouachée)|(aquarelle)|(lithographique)|(plomb)|(huile)|(cuivre)|(toile)|(bronze)|(Plâtre)|(en\s+terre\s+de\s+faïence)|(polycarbonate\s+alvéolaire)|(acrylique)|(jute)|(photographie\s+en\s+couleur)|(gouache)|(terre\s+cuite)|(sur\s+panneau)|(lithographie)|(sur\s+carton)|(céramique)|(cibachrome)|(Saupoudreuse)|(argent)|(Sanguine)|(pierre\s+noire)", re.IGNORECASE|re.DOTALL)
        signedPattern = re.compile("signed", re.IGNORECASE)
        editionPattern = re.compile("edition", re.IGNORECASE)
        editionPattern2 = re.compile("Numéroté", re.IGNORECASE)
        sizePattern0 = re.compile("H_([\d,\.]+)\s+([a-zA-Z]{2})\s+L_([\d\.,]+)\s+([a-zA-Z]{2})")
        sizePattern = re.compile("([\d\s\.,_HLDWcmin]+\s+cm)", re.IGNORECASE)
        sizePattern1 = re.compile("([\d,]+\s*x\s*[\d,]+\s*cm)", re.IGNORECASE)
        sizePattern2 = re.compile("([\d,]+\s*cm)", re.IGNORECASE)
        measureunitPattern = re.compile("([a-zA-Z]{2})")
        beginspacePattern = re.compile("^\s+")
        brPattern = re.compile("<br\s*\/?>", re.IGNORECASE)
        whitespacePattern = re.compile("^\s*$")
        starthyphenPattern = re.compile("^\s+-\s+")
        artistnamePattern1 = re.compile("(.*?)\s+\((\d{4})\-?(\d{0,4})\)")
        artistnamePattern2 = re.compile("(.*?)\s+\(n[éÉE]{1}E?\s+en\s+(\d{4})\)", re.IGNORECASE)
        artistnamePattern3 = re.compile("(.*?)\s+\(N[ÉE]{1}E?\s+(\d{4})\)", re.IGNORECASE)
        provenancePattern = re.compile("Provenance\:", re.IGNORECASE)
        yearPattern1 = re.compile(",\s+(\d{4})\-(\d{4})")
        yearPattern2 = re.compile(",\s+circa\s+(\d{4})")
        yearPattern3 = re.compile(",\s+(\d{4})")
        matcatdict_en = {}
        matcatdict_fr = {}
        #with open("docs/fineart_materials.csv", newline='') as mapfile:
        with open("/root/artwork/deploydirnew/docs/fineart_materials.csv", newline='') as mapfile:
            mapreader = csv.reader(mapfile, delimiter=",", quotechar='"')
            for maprow in mapreader:
                matcatdict_en[maprow[1]] = maprow[3]
                matcatdict_fr[maprow[2]] = maprow[3]
        mapfile.close()
        artistname, artworkname = "", ""
        artistinfodivtags = soup.find_all("div", {'class' : 'fiche_titre_lot'})
        titletagcontent = ""
        if artistinfodivtags.__len__() > 0:
            artistinfo = artistinfodivtags[0].renderContents().decode('utf-8')
            artistinfo = artistinfo.replace("\n", "").replace("\r", "")
            artistinfo = self.__class__.htmltagPattern.sub("", artistinfo)
            titletagcontent = artistinfo
            aps1 = re.search(artistnamePattern1, artistinfo)
            aps2 = re.search(artistnamePattern2, artistinfo)
            aps3 = re.search(artistnamePattern3, artistinfo)
            if aps1:
                artistname = aps1.groups()[0]
                artistname = beginspacePattern.sub("", artistname)
                artistbdate = aps1.groups()[1]
                artistddate = aps1.groups()[2]
                detailData['artist_name'] = artistname
                detailData['artist_birth'] = artistbdate
                detailData['artist_death'] = artistddate
            elif aps2:
                artistname = str(aps2.groups()[0])
                if not artistname or artistname == "None":
                    artistname = ""
                artistname = beginspacePattern.sub("", artistname)
                artistbdate = str(aps2.groups()[1])
                detailData['artist_name'] = artistname
                detailData['artist_birth'] = artistbdate
                detailData['artist_death'] = ""
            elif aps3:
                artistname = str(aps3.groups()[0])
                if not artistname or artistname == "None":
                    artistname = ""
                artistname = beginspacePattern.sub("", artistname)
                artistbdate = str(aps3.groups()[1])
                detailData['artist_name'] = artistname
                detailData['artist_birth'] = artistbdate
                detailData['artist_death'] = ""
            else:
                artistinfo = beginspacePattern.sub("", artistinfo)
                detailData['artist_name'] = artistinfo
                detailData['artist_birth'] = ""
                detailData['artist_death'] = ""
            artistname = detailData['artist_name']
        descdivtags = soup.find_all("div", {'class' : 'fiche_lot_description'})
        if descdivtags.__len__() > 0:
            descdivcontents = descdivtags[0].renderContents().decode('utf-8')
            descdivcontents = descdivcontents.replace("\n", "").replace("\r", "")
            detailData['artwork_description'] = descdivcontents
            descparts = re.split(brPattern, descdivcontents)
            if not re.search(whitespacePattern, descparts[0]):
                detailData['artwork_name'] = descparts[0]
            else:
                detailData['artwork_name'] = descparts[1]
            detailData['artwork_name'] = beginspacePattern.sub("", detailData['artwork_name'])
            detailData['artwork_name'] = detailData['artwork_name'].replace('"', "'")
            yps1 = re.search(yearPattern1, detailData['artwork_name'])
            yps2 = re.search(yearPattern2, detailData['artwork_name'])
            yps3 = re.search(yearPattern3, detailData['artwork_name'])
            if yps1:
                yearfrom = yps1.groups()[0]
                yearto = yps1.groups()[1]
                detailData['artwork_name'] = yearPattern1.sub("", detailData['artwork_name'])
                detailData['artwork_start_year'] = str(yearfrom)
                detailData['artwork_end_year'] = str(yearto)
            elif yps2:
                yearfrom = yps2.groups()[0]
                detailData['artwork_name'] = yearPattern2.sub("", detailData['artwork_name'])
                detailData['artwork_start_year'] = str(yearfrom)
                detailData['artwork_end_year'] = ""
            elif yps3:
                yearfrom = yps3.groups()[0]
                detailData['artwork_name'] = yearPattern3.sub("", detailData['artwork_name'])
                detailData['artwork_start_year'] = str(yearfrom)
                detailData['artwork_end_year'] = ""
            else:
                pass
            artworkname = detailData['artwork_name']
            dctr = 0
            for dpart in descparts:
                mps = re.search(mediumPattern, dpart)
                nemps = re.search(nonenglishmediumPattern, dpart)
                if mps and 'artwork_materials' not in detailData.keys():
                    detailData['artwork_materials'] = dpart
                    detailData['artwork_materials'] = beginspacePattern.sub("", detailData['artwork_materials'])
                if not mps and nemps and 'artwork_materials' not in detailData.keys():
                    detailData['artwork_materials'] = dpart
                    detailData['artwork_materials'] = beginspacePattern.sub("", detailData['artwork_materials'])
                sps = re.search(signedPattern, dpart)
                if sps and 'artwork_markings' not in detailData.keys():
                    detailData['artwork_markings'] = dpart
                    detailData['artwork_markings'] = beginspacePattern.sub("", detailData['artwork_markings'])
                    detailData['artwork_markings'] = detailData['artwork_markings'].replace('"', "'")
                zps0 = re.search(sizePattern0, dpart)
                zps = re.search(sizePattern, dpart)
                zps1 = re.search(sizePattern1, dpart)
                zps2 = re.search(sizePattern2, dpart)
                if zps0 and 'artwork_size_notes' not in detailData.keys():
                    height = zps0.groups()[0]
                    unit = zps0.groups()[1]
                    width = zps0.groups()[2]
                    detailData['artwork_size_notes'] = str(height) + " x " + str(width) + " " + unit
                elif zps and 'artwork_size_notes' not in detailData.keys():
                    detailData['artwork_size_notes'] = zps.groups()[0]
                elif zps1 and 'artwork_size_notes' not in detailData.keys():
                    detailData['artwork_size_notes'] = zps1.groups()[0]
                elif zps2 and 'artwork_size_notes' not in detailData.keys():
                    detailData['artwork_size_notes'] = zps2.groups()[0]
                dctr += 1
                pps = re.search(provenancePattern, dpart)
                if pps:
                    if 'artwork_provenance' not in detailData.keys():
                        detailData['artwork_provenance'] = ""
                        for line in descparts[dctr:]:
                            detailData['artwork_provenance'] += " " + line
                        detailData['artwork_provenance'] = detailData['artwork_provenance'].replace('"', "'")
                        detailData['artwork_provenance'] = starthyphenPattern.sub("", detailData['artwork_provenance'])
                        break # Breaking out of the outer loop.
            detailData['artwork_description'] = titletagcontent + " " + detailData['artwork_description'].strip()
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
            detailData['artwork_description'] = detailData['artwork_description'].replace('"', "'")
        if 'artwork_size_notes' in detailData.keys():
            sizeparts = detailData['artwork_size_notes'].split("x")
            mups = re.search(measureunitPattern, sizeparts[0])
            if mups:
                detailData['auction_measureunit'] = mups.groups()[0]
                sizeparts[0] = measureunitPattern.sub("", sizeparts[0])
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
        nonartistPattern = re.compile("Lot\s+\d+\s+\-\s+Pierre\s+Bergé\s+&amp;\s+Associés", re.IGNORECASE)
        naps = re.search(nonartistPattern, detailData['artist_name']) # If the above pattern exists in artist's name, then actually it is the artwork name, and not artist's name.
        if naps:
            detailData['artwork_name'] = detailData['artist_name']
            detailData['artist_name'] = ""
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
        noscripttags = soup.find_all("noscript")
        defaultimgrl = ""
        if noscripttags.__len__() > 0:
            imgtags = noscripttags[0].find_all("img")
            if imgtags.__len__() > 0:
                defaultimgurl = imgtags[0]['src']
        imagename1 = self.getImagenameFromUrl(defaultimgrl)
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
        imagepathparts = defaultimgrl.split("/")
        defimageurl = "/".join(imagepathparts[:-2])
        encryptedFilename = str(encryptedFilename).replace("b'", "")
        encryptedFilename = str(encryptedFilename).replace("'", "")
        detailData['image1_name'] = str(encryptedFilename) + ".jpg"
        detailData['artwork_images1'] = defaultimgrl
        detailData['auction_house_name'] = "PIERRE BERGÉ"
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
        baseUrl = "https://www.pba-auctions.com"
        info = []
        endspacePattern = re.compile("\s+$", re.DOTALL)
        soldpricePattern = re.compile("([\d\s\.,]+)\s+€")
        beginspacePattern = re.compile("^\s+")
        multispacePattern = re.compile("\s+")
        for htmldiv in htmlList:
            data = {}
            data['auction_num'] = self.saleno
            lotno = ""
            htmlContent = htmldiv.renderContents().decode('utf-8')
            s = BeautifulSoup(htmlContent, features="html.parser")
            allanchors = s.find_all("a")
            htmlanchor = allanchors[0]
            detailUrl = baseUrl + htmlanchor['href']
            data['lot_origin_url'] = detailUrl
            lotnospantags = s.find_all("span", {'class' : 'lotnum'})
            if lotnospantags.__len__() > 0:
                lotnocontents = lotnospantags[0].renderContents().decode('utf-8')
                lotnocontents = lotnocontents.replace("\n", "").replace("\r", "")
                lotnocontents = beginspacePattern.sub("", lotnocontents)
                lotnocontents = endspacePattern.sub("", lotnocontents)
                lotno = lotnocontents
            if not lotno:
                continue
            data['lot_num'] = lotno
            estimatedivtags = s.find_all("div", {'class' : 'estimAff4'})
            if estimatedivtags.__len__() > 0:
                estimate = estimatedivtags[0].renderContents().decode('utf-8')
                estimate = estimate.replace("\n", "").replace("\r", "")
                estimate = beginspacePattern.sub("", estimate)
                estimate = endspacePattern.sub("", estimate)
                estimate = multispacePattern.sub(" ", estimate)
                estimateparts = estimate.split(" - ")
                data['price_estimate_min'] = estimateparts[0]
                if estimateparts.__len__() > 1:
                    data['price_estimate_max'] = estimateparts[1]
                    currencyPattern = re.compile("\s+[a-zA-Z]{3}")
                    data['price_estimate_max'] = currencyPattern.sub("", data['price_estimate_max'])
            soldpricedivtags = s.find_all("div", {'class' : 'sale-flash2'})
            if soldpricedivtags.__len__() > 0:
                soldpricecontents = soldpricedivtags[0].renderContents().decode('utf-8')
                soldpricecontents = soldpricecontents.replace("\n", " ").replace("\r", "")
                soldpricecontents = self.__class__.htmltagPattern.sub("", soldpricecontents)
                soldpricecontents = soldpricecontents.replace("Résultat", "")
                soldpricecontents = soldpricecontents.replace("Result", "")
                soldpricecontents = multispacePattern.sub(" ", soldpricecontents)
                soldpricecontents = beginspacePattern.sub("", soldpricecontents)
                soldpricecontents = endspacePattern.sub("", soldpricecontents)
                data['price_sold'] = soldpricecontents
            else:
                data['price_sold'] = "0"
            """
            try:
                print(data['lot_num'] + " ## " + data['price_estimate_min'] + " ## " + data['price_sold'])
            except:
                print(data['lot_num'])
            """
            print("Getting '%s'..."%data['lot_origin_url'])
            detailsPageContent = self.getDetailsPage(detailUrl)
            if not lotno:
                continue
            detailData = self.parseDetailPage(detailsPageContent, lotno, imagepath, downloadimages)
            for k in detailData.keys():
                data[k] = detailData[k]
            withdrawnPattern = re.compile("withdrawn", re.IGNORECASE|re.DOTALL)
            data['price_kind'] = "unknown"
            if ('price_sold' in data.keys() and re.search(withdrawnPattern, data['price_sold'])) or ('price_estimate_max' in data.keys() and re.search(withdrawnPattern, data['price_estimate_max'])):
                data['price_kind'] = "withdrawn"
            elif 'price_sold' in data.keys() and data['price_sold'] != "" and str(data['price_sold']) != "0":
                data['price_kind'] = "price realized"
            elif 'price_estimate_max' in data.keys() and data['price_estimate_max'] != "":
                data['price_kind'] = "estimate"
            else:
                pass
            if 'price_sold' not in data.keys() or str(data['price_sold']) == "0":
                data['price_sold'] = ""
            data['auction_start_date'] = self.__class__.formatDate(self.auctiondate)
            data['auction_start_date'] = data['auction_start_date'].replace("\n", " ").replace("\r\n", " ")
            data['auction_name'] = self.auctiontitle
            data['auction_location'] = "Paris"
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
    pageurl = "http://216.137.189.57:8080/scrapers/finish/?scrapername=Pierreberge&auctionnumber=%s&auctionurl=%s&scrapertype=2"%(auctionno, urllib.parse.quote(auctionurl))
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
    pba = PierreBergeBot(auctionurl, auctionnumber)
    fp = open(csvpath, "w")
    fieldnames = ['auction_house_name', 'auction_location', 'auction_num', 'auction_start_date', 'auction_end_date', 'auction_name', 'lot_num', 'sublot_num', 'price_kind', 'price_estimate_min', 'price_estimate_max', 'price_sold', 'artist_name', 'artist_birth', 'artist_death', 'artist_nationality', 'artwork_name', 'artwork_year_identifier', 'artwork_start_year', 'artwork_end_year', 'artwork_materials', 'artwork_category', 'artwork_markings', 'artwork_edition', 'artwork_description', 'artwork_measurements_height', 'artwork_measurements_width', 'artwork_measurements_depth', 'artwork_size_notes', 'auction_measureunit', 'artwork_condition_in', 'artwork_provenance', 'artwork_exhibited', 'artwork_literature', 'artwork_images1', 'artwork_images2', 'artwork_images3', 'artwork_images4', 'artwork_images5', 'image1_name', 'image2_name', 'image3_name', 'image4_name', 'image5_name', 'lot_origin_url']
    fieldsstr = ",".join(fieldnames)
    fp.write(fieldsstr + "\n")
    pagectr = 1
    offset = 0
    maxblock = 50
    while True:
        soup = BeautifulSoup(pba.currentPageContent, features="html.parser")
        lotsdata = pba.getLotsFromPage()
        if lotsdata.__len__() == 0:
            break
        info = pba.getInfoFromLotsData(lotsdata, imagepath, downloadimages)
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
        offset = offset + maxblock
        nextpageUrl = auctionurl + "?lang=fr&offset=%s&max=%s&sold="%(offset, maxblock)
        pba.pageRequest = urllib.request.Request(nextpageUrl, headers=pba.httpHeaders)
        try:
            pba.pageResponse = pba.opener.open(pba.pageRequest)
        except:
            print("Couldn't find the page %s"%str(pagectr))
            break
        pba.currentPageContent = pba.__class__._decodeGzippedContent(pba.getPageContent())
    fp.close()
    updatestatus(auctionnumber, auctionurl)

# Example: python pierreberge.py https://www.pba-auctions.com/catalogue/111543 111543 /home/supmit/work/art2/pierreberge_111543.csv /home/supmit/work/art2/images/pierreberge/111543 0 0

# supmit

