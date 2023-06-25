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


class KarlandFaberBot(object):
    
    startUrl=r"https://www.karlundfaber.de/auction-catalog/modern-art_OH64A0G02J?pageNum=1"
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
        self.httpHeaders = { 'User-Agent' : r'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36',  'Accept' : 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8', 'Accept-Language' : 'en-GB,en-US;q=0.9,en;q=0.8', 'Accept-Encoding' : 'gzip,deflate,br', 'Accept-Charset' : 'ISO-8859-1,utf-8;q=0.7,*;q=0.7', 'Keep-Alive' : '115', 'Connection' : 'keep-alive', }
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
        allh1tags = soup.find_all("h1")
        if allh1tags.__len__() > 0:
            title = allh1tags[0].renderContents().decode('utf-8')
            self.auctiontitle = title
        self.auctiontitle
        classPattern = re.compile("^teaser")
        lotblocks = soup.find_all("article", {'class' : classPattern})
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
        baseUrl = "https://www.karlundfaber.de"
        detailData = {}
        soup = BeautifulSoup(detailsPage, features="html.parser")
        mediumPattern = re.compile("(gold)|(silver)|(brass)|(bronze)|(wood)|(porcelain)|(stone)|(marble)|(metal)|(steel)|(iron)|(glass)|(plexiglas)|(chromogenic)|(paper)|(canvas)|(masonite)|(newsprint)|(silkscreen)|(parchment)|(linen)|(inkjet)|(ink\s+jet)|(pigment)|(\stin\s)|(photogravure)|(^oil\s+)|(\s+panel\s+)|(terracotta)|(ivory)|(\s+oak\s+)|(^oak\s+)|(\s+oak$)|(alabaster)|(\s+ink\s+)|(\s+ink\,)|(\s+chalk\s+)|(chalk\s+)|(\s+etching\s+)|(watercolour)|(watercolor)|(pencil)|(pastel)|(lino\s+print)|(charcoal)|(lithograph)|(gouache)|(woven)|(embossing)|(cardboard)", re.DOTALL|re.IGNORECASE)
        nonenglishmediumPattern = re.compile("(crayon)|(encre)|(plume)|(plume\s+et\s+encre)|(papier)|(pastel)|(craie)|(gouachée)|(aquarelle)|(lithographique)|(plomb)|(huile)|(cuivre)|(toile)|(bronze)|(Plâtre)|(en\s+terre\s+de\s+faïence)|(\s+velin)|(radierung)|(aquarelliert)|(holzschnitt)|(\s+karton)|(Öl\s+)|(\s+holz)|(holz\s+)|(leinwand)|(aquarell)|(tusche)|(\s+filz)|(graupappe)|(serigraphie)|(lithographie)|(tonpapier)", re.IGNORECASE|re.DOTALL)
        signedPattern = re.compile("signed", re.IGNORECASE)
        signedPattern2 = re.compile("signiert", re.IGNORECASE|re.DOTALL)
        editionPattern = re.compile("édition", re.IGNORECASE)
        editionPattern2 = re.compile("Numéroté", re.IGNORECASE)
        sizePattern0 = re.compile("([\d\.,]+\s*\:\s*[\d\.,]+\s+cm)", re.IGNORECASE|re.DOTALL)
        sizePattern = re.compile("([\d,\.]+\s*x\s*[\d,\.]+\s*cm)\.?", re.IGNORECASE)
        sizePattern2 = re.compile("([\d,\.]+\s*cm)", re.IGNORECASE)
        bioPattern = re.compile("^(\d{4}).*?(\d*)$", re.DOTALL)
        provenancePattern = re.compile("Provenienz\:", re.IGNORECASE|re.DOTALL)
        exhibitionPattern = re.compile("Ausstellung\:", re.IGNORECASE|re.DOTALL)
        datePattern = re.compile("(\d{1,2}\s+\w+\s+\d{4})")
        beginspacePattern = re.compile("^\s+")
        brPattern = re.compile("<br\s*\/?>", re.IGNORECASE)
        measureunitPattern = re.compile("([a-zA-Z]{2})")
        matcatdict_en = {}
        matcatdict_fr = {}
        #with open("docs/fineart_materials.csv", newline='') as mapfile:
        with open("/root/artwork/deploydirnew/docs/fineart_materials.csv", newline='') as mapfile:
            mapreader = csv.reader(mapfile, delimiter=",", quotechar='"')
            for maprow in mapreader:
                matcatdict_en[maprow[1]] = maprow[3]
                matcatdict_fr[maprow[2]] = maprow[3]
        mapfile.close()
        biodivtags = soup.find_all("div", {'class' : 'artwork-artistbio'})
        if biodivtags.__len__() > 0:
            biodiv = biodivtags[0]
            biocontents = biodiv.renderContents().decode('utf-8')
            bps = re.search(bioPattern, biocontents)
            if bps:
                detailData['artist_birth'] = bps.groups()[0]
                detailData['artist_death'] = bps.groups()[1]
        shortdescdivtags = soup.find_all("div", {'class' : 'artwork-shortdescription'})
        if shortdescdivtags.__len__() > 0:
            shortdescdiv = shortdescdivtags[0]
            shortdesc = shortdescdiv.renderContents().decode('utf-8')
            zps0 = re.search(sizePattern0, shortdesc)
            if zps0 and 'artwork_size_notes' not in detailData.keys():
                zpsg0 = zps0.groups()
                detailData['artwork_size_notes'] = zpsg0[0]
                detailData['artwork_size_notes'] = detailData['artwork_size_notes'].replace(",", ".").replace(":", "x")
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
            zps = re.search(sizePattern, shortdesc)
            if zps and 'artwork_size_notes' not in detailData.keys():
                zpsg = zps.groups()
                detailData['artwork_size_notes'] = zpsg[0]
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
            zps2 = re.search(sizePattern2, shortdesc)
            if zps2 and 'artwork_size_notes' not in detailData.keys():
                zpsg2 = zps2.groups()
                detailData['artwork_size_notes'] = zpsg2[0]
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
            shortdescparts = shortdesc.split(".")
            for shortdescpart in shortdescparts:
                sps = re.search(signedPattern, shortdescpart)
                if sps and 'artwork_markings' not in detailData.keys():
                    detailData['artwork_markings'] = shortdescpart
                    detailData['artwork_markings'] = beginspacePattern.sub("", detailData['artwork_markings'])
                sps2 = re.search(signedPattern2, shortdescpart)
                if sps2 and 'artwork_markings' not in detailData.keys():
                    detailData['artwork_markings'] = shortdescpart
                    detailData['artwork_markings'] = beginspacePattern.sub("", detailData['artwork_markings'])
                mps = re.search(mediumPattern, shortdescpart)
                if mps and 'artwork_materials' not in detailData.keys():
                    detailData['artwork_materials'] = shortdescpart
                    detailData['artwork_materials'] = beginspacePattern.sub("", detailData['artwork_materials'])
                nemps = re.search(nonenglishmediumPattern, shortdescpart)
                if nemps and 'artwork_materials' not in detailData.keys():
                    detailData['artwork_materials'] = shortdescpart
                    detailData['artwork_materials'] = beginspacePattern.sub("", detailData['artwork_materials'])
        # Get images
        defaultimageurl = ""
        allimageanchortags = soup.find_all("a", {'class' : 'glightbox'})
        if allimageanchortags.__len__() > 0:
            defaultanchortag = allimageanchortags[0]
            defaultimgtags = defaultanchortag.findChildren("img", recursive=False)
            if defaultimgtags.__len__() > 0:
                defaultimageurl = defaultimgtags[0]['src']
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
        altimageurls = []
        if allimageanchortags.__len__() > 1:
            for imageanchortag in allimageanchortags[1:]:
                altimgtags = imageanchortag.findChildren("img", recursive=False)
                if altimgtags.__len__() > 0:
                    altimgtag = altimgtags[0]
                    altimageurls.append(altimgtag['src'])
        imgctr = 2
        if altimageurls.__len__() > 0:
            altimage2 = altimageurls[0]
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
        if altimageurls.__len__() > 1:
            altimage2 = altimageurls[1]
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
        if altimageurls.__len__() > 2:
            altimage2 = altimageurls[2]
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
        if altimageurls.__len__() > 3:
            altimage2 = altimageurls[3]
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
        aucdatedivtags = soup.find_all("div", {'class' : 'artwork-auction'})
        if aucdatedivtags.__len__() > 0:
            aucdatediv = aucdatedivtags[0]
            aucdatedivcontents = aucdatediv.renderContents().decode('utf-8')
            aucdatedivcontents = aucdatedivcontents.replace("\n", "").replace("\r", "")
            aucdatedivcontents = self.__class__.htmltagPattern.sub("", aucdatedivcontents)
            dps = re.search(datePattern, aucdatedivcontents)
            if dps:
                detailData['auction_start_date'] = dps.groups()[0]
                self.auctiondate = detailData['auction_start_date']
        detailData['auction_house_name'] = "KARL & FABER"
        provdivtags = soup.find_all("div", {'class' : 'richtext'})
        for provdivtag in provdivtags:
            provdivcontent = provdivtag.renderContents().decode('utf-8')
            pps = re.search(provenancePattern, provdivcontent)
            if pps:
                allparas = provdivtag.find_all("p")
                for para in allparas:
                    paracontent = para.renderContents().decode('utf-8')
                    paracontent = paracontent.replace("\n", "").replace("\r", "")
                    pps2 = re.search(provenancePattern, paracontent)
                    if pps2:
                        brparts = re.split(brPattern, paracontent)
                        detailData['artwork_provenance'] = ""
                        provenanceFlag = 0
                        exhibitionFlag = 0
                        for brpart in brparts:
                            if re.search(provenancePattern, brpart):
                                provenanceFlag = 1
                                continue
                            xpsflag = re.search(exhibitionPattern, brpart)
                            if xpsflag:
                                exhibitionFlag = 1
                                break
                            if provenanceFlag and not exhibitionFlag:
                                detailData['artwork_provenance'] += brpart
                        detailData['artwork_provenance'] = self.__class__.htmltagPattern.sub("", detailData['artwork_provenance'])
                        detailData['artwork_provenance'] = beginspacePattern.sub("", detailData['artwork_provenance'])
                        detailData['artwork_provenance'] = detailData['artwork_provenance'].replace('"', "'")
            xps = re.search(exhibitionPattern, provdivcontent)
            if xps:
                allparas = provdivtag.find_all("p")
                for para in allparas:
                    paracontent = para.renderContents().decode('utf-8')
                    paracontent = paracontent.replace("\n", "").replace("\r", "")
                    xps2 = re.search(exhibitionPattern, paracontent)
                    if xps2:
                        brparts = re.split(brPattern, paracontent)
                        detailData['artwork_exhibited'] = ""
                        provenanceFlag = 0
                        exhibitionFlag = 0
                        for brpart in brparts:
                            if re.search(exhibitionPattern, brpart):
                                exhibitionFlag = 1
                                continue
                            prvflag = re.search(provenancePattern, brpart)
                            if prvflag:
                                provenanceFlag = 1
                                break
                            if exhibitionFlag and not provenanceFlag:
                                detailData['artwork_exhibited'] += brpart
                        detailData['artwork_exhibited'] = self.__class__.htmltagPattern.sub("", detailData['artwork_exhibited'])
                        detailData['artwork_exhibited'] = beginspacePattern.sub("", detailData['artwork_exhibited'])
                        detailData['artwork_exhibited'] = detailData['artwork_exhibited'].replace('"', "'")
        if 'artwork_materials' in detailData.keys() and 'artwork_category' not in detailData.keys():
            detailData['artwork_materials'] = self.__class__.htmltagPattern.sub("", detailData['artwork_materials'])
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
        sidebarsectiondivtags = soup.find_all("div", {'class' : 'sidebar-section'})
        if sidebarsectiondivtags.__len__() > 0:
            sidebartext = sidebarsectiondivtags[0].renderContents().decode('utf-8')
            sidebartext = self.__class__.htmltagPattern.sub("", sidebartext)
            detailData['artwork_description'] = sidebartext
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
        baseUrl = "https://www.karlundfaber.de"
        info = []
        endSpacePattern = re.compile("\s+$", re.DOTALL)
        lotno = ""
        for htmlart in htmlList:
            data = {}
            data['auction_num'] = self.saleno
            detailUrl = ""
            artistname, artworkname = "", ""
            htmlContent = htmlart.renderContents().decode('utf-8')
            s = BeautifulSoup(htmlContent, features="html.parser")
            lotnodivtags = s.find_all("div", {'class' : 'artwork-meta'})
            if lotnodivtags.__len__() > 0:
                lotnodiv = lotnodivtags[0]
                lotnocontent = lotnodiv.renderContents().decode('utf-8')
                lotnocontent = lotnocontent.replace("\n", "").replace("\r", "")
                lotPattern = re.compile("Lot\s+(\d+)", re.IGNORECASE|re.DOTALL)
                lps = re.search(lotPattern, lotnocontent)
                if lps:
                    data['lot_num'] = lps.groups()[0]
                    lotno = data['lot_num']
            artistdivtags = s.find_all("div", {'class' : 'artwork-artist'})
            if artistdivtags.__len__() > 0:
                artistdiv = artistdivtags[0]
                artistcontent = artistdiv.renderContents().decode('utf-8')
                artistcontent = artistcontent.replace("\n", "").replace("\r", "")
                data['artist_name'] = artistcontent
                artistname = data['artist_name']
            titledivtags = s.find_all("div", {'class' : 'artwork-title'})
            if titledivtags.__len__() > 0:
                titlediv = titledivtags[0]
                title = titlediv.renderContents().decode('utf-8')
                data['artwork_name'] = title
                artworkname = data['artwork_name']
            estimatedivtags = s.find_all("div", {'class' : 'artwork-price'})
            if estimatedivtags.__len__() > 0:
                estimatediv = estimatedivtags[0]
                estimatecontents = estimatediv.renderContents().decode('utf-8')
                resultsPattern = re.compile("Result\:", re.IGNORECASE|re.DOTALL)
                estimatecontents = estimatecontents.replace("\n", "").replace("\r", "")
                estimatePattern = re.compile("\s+([\d\.\,]+)\*?\/?([\d\.\,]*)\s+", re.DOTALL)
                eps = re.search(estimatePattern, estimatecontents)
                if eps:
                    epsg = eps.groups()
                    low = epsg[0]
                    high = epsg[1]
                    data['price_estimate_min'] = low
                    if high:
                        data['price_estimate_max'] = high
                rps = re.search(resultsPattern, estimatecontents)
                if rps and 'price_estimate_min' in data.keys():
                    data['price_sold'] = data['price_estimate_min']
                    data['price_estimate_min'] = ""
            allanchors = s.find_all("a")
            htmlanchor = allanchors[0]
            detailUrl = htmlanchor['href']
            data['lot_origin_url'] = detailUrl
            #print(data['lot_num'] + " ## " + data['artist_name'] + " ## " + data['artwork_name'] + " ## " + data['price_estimate_min'])
            print("Getting '%s'..."%data['lot_origin_url'])
            detailsPageContent = self.getDetailsPage(detailUrl)
            detailData = self.parseDetailPage(detailsPageContent, lotno, imagepath, artistname, artworkname, downloadimages)
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
            data['auction_start_date'] = self.__class__.formatDate(self.auctiondate)
            data['auction_start_date'] = data['auction_start_date'].replace("\n", " ").replace("\r\n", " ")
            data['auction_name'] = self.auctiontitle
            data['auction_location'] = "Munich"
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
    pageurl = "http://216.137.189.57:8080/scrapers/finish/?scrapername=KarlandFaber&auctionnumber=%s&auctionurl=%s&scrapertype=2"%(auctionno, urllib.parse.quote(auctionurl))
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
    karlandfaber = KarlandFaberBot(auctionurl, auctionnumber)
    fp = open(csvpath, "w")
    fieldnames = ['auction_house_name', 'auction_location', 'auction_num', 'auction_start_date', 'auction_end_date', 'auction_name', 'lot_num', 'sublot_num', 'price_kind', 'price_estimate_min', 'price_estimate_max', 'price_sold', 'artist_name', 'artist_birth', 'artist_death', 'artist_nationality', 'artwork_name', 'artwork_year_identifier', 'artwork_start_year', 'artwork_end_year', 'artwork_materials', 'artwork_category', 'artwork_markings', 'artwork_edition', 'artwork_description', 'artwork_measurements_height', 'artwork_measurements_width', 'artwork_measurements_depth', 'artwork_size_notes', 'auction_measureunit', 'artwork_condition_in', 'artwork_provenance', 'artwork_exhibited', 'artwork_literature', 'artwork_images1', 'artwork_images2', 'artwork_images3', 'artwork_images4', 'artwork_images5', 'image1_name', 'image2_name', 'image3_name', 'image4_name', 'image5_name', 'lot_origin_url']
    fieldsstr = ",".join(fieldnames)
    fp.write(fieldsstr + "\n")
    pagectr = 1
    while True:
        soup = BeautifulSoup(karlandfaber.currentPageContent, features="html.parser")
        lotsdata = karlandfaber.getLotsFromPage()
        info = karlandfaber.getInfoFromLotsData(lotsdata, imagepath, downloadimages)
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
        nextpageanchors = soup.find_all("a", {'class' : 'is-icon icon--nextpage'})
        if nextpageanchors.__len__() > 0:
            nextpageUrl = nextpageanchors[0]['href']
            try:
                response = requests.get(nextpageUrl)
                karlandfaber.currentPageContent = response.text
            except:
                print("Couldn't find the page %s"%str(pagectr))
                break
        else:
            break
    fp.close()
    updatestatus(auctionnumber, auctionurl)

# Example: python karlandfaber.py https://www.karlundfaber.de/en/auctions/303/modern-art/ 303 /home/supmit/work/art2/karlandfaber_303.csv /home/supmit/work/art2/images/karlandfaber/303 0 0


# supmit

