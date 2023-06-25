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


class JohnMoranBot(object):
    
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
        pageContent = self.currentPageContent
        soup = BeautifulSoup(pageContent, features="html.parser")
        alltitletags = soup.find_all("title")
        if alltitletags.__len__() > 0:
            title = alltitletags[0].renderContents().decode('utf-8')
            title = title.replace("Catalog - ", "")
            beginspacePattern = re.compile("^\s+")
            endspacePattern = re.compile("\s+$")
            title = beginspacePattern.sub("", title)
            title = endspacePattern.sub("", title)
            self.auctiontitle = title
        lotblocks = soup.find_all("div", {'class' : 'lot-title-block'})
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
        baseUrl = "https://www.johnmoran.com"
        detailData = {}
        soup = BeautifulSoup(detailsPage, features="html.parser")
        mediumPattern = re.compile("(gold)|(silver)|(brass)|(bronze)|(wood)|(porcelain)|(stone)|(marble)|(metal)|(steel)|(iron)|(glass)|(plexiglas)|(chromogenic)|(paper)|(canvas)|(masonite)|(newsprint)|(silkscreen)|(parchment)|(linen)|(inkjet)|(ink\s+jet)|(pigment)|(\stin\s)|(photogravure)|(^oil\s+)|(\s+panel\s+)|(terracotta)|(ivory)|(\s+oak\s+)|(^oak\s+)|(\s+oak$)|(alabaster)", re.DOTALL|re.IGNORECASE)
        nonenglishmediumPattern = re.compile("(crayon)|(encre)|(plume)|(plume\s+et\s+encre)|(papier)|(pastel)|(craie)|(gouachée)|(aquarelle)|(lithographique)|(plomb)|(huile)|(cuivre)|(toile)|(bronze)|(Plâtre)|(en\s+terre\s+de\s+faïence)", re.IGNORECASE|re.DOTALL)
        signedPattern = re.compile("signed", re.IGNORECASE)
        editionPattern = re.compile("(Edition\s+[\d\/]+),\s+(signed\s+.*)", re.IGNORECASE)
        editionPattern2 = re.compile("(Edition\s+of\s+[\d]+);\s+(signed\s+.*)", re.IGNORECASE)
        sizePattern = re.compile("([\d\.]+\"\s+H\s+x\s+[\d\.]+\"\s+W\s+x\s+[\d\.]+\"\s+D)", re.IGNORECASE)
        sizePattern2 = re.compile("([\d\.]+\"\s+H\s+x\s+[\d\.]+\"\s+W)", re.IGNORECASE)
        sizePattern3 = re.compile("([\d\.]+\"\s+H)", re.IGNORECASE)
        sizePattern4 = re.compile("([\d\.]+\"\s+L)", re.IGNORECASE)
        provenancePattern = re.compile("provenance:\s+(.*)", re.IGNORECASE)
        literaturePattern = re.compile("literature:\s+(.*)", re.IGNORECASE)
        exhibitionPattern = re.compile("exhibited:\s+(.*)", re.IGNORECASE)
        beginspacePattern = re.compile("^\s+")
        alldescdiv = soup.find_all("div", {'id' : 'lotDescriptionFields'})
        if alldescdiv.__len__() > 0:
            alldivs = alldescdiv[0].find_all("div")
            dctr = 0
            for i in range(0, alldivs.__len__()):
                divcontents = alldivs[i].renderContents().decode('utf-8')
                divcontents = divcontents.replace("\n", " ").replace("\r", " ")
                if i == 0:
                    detailData['artwork_materials'] = divcontents
                elif i == 1:
                    eps = re.search(editionPattern, divcontents)
                    eps2 = re.search(editionPattern2, divcontents)
                    if eps:
                        epsg = eps.groups()
                        detailData['artwork_edition'] = epsg[0]
                        detailData['artwork_markings'] = epsg[1]
                    elif eps2:
                        epsg2 = eps2.groups()
                        detailData['artwork_edition'] = epsg2[0]
                        detailData['artwork_markings'] = epsg2[1]
                    else:
                        sps = re.search(signedPattern, divcontents)
                        if sps:
                            detailData['artwork_markings'] = divcontents
                elif i == 2:
                    zps1 = re.search(sizePattern, divcontents)
                    zps2 = re.search(sizePattern2, divcontents)
                    zps3 = re.search(sizePattern3, divcontents)
                    zps4 = re.search(sizePattern4, divcontents)
                    if zps1:
                        divcontents = divcontents.replace('"', "in")
                        detailData['artwork_size_notes'] = divcontents
                    elif zps2:
                        divcontents = divcontents.replace('"', "in")
                        detailData['artwork_size_notes'] = divcontents
                    elif zps3:
                        divcontents = divcontents.replace('"', "in")
                        detailData['artwork_size_notes'] = divcontents
                    elif zps4:
                        divcontents = divcontents.replace('"', "in")
                        detailData['artwork_size_notes'] = divcontents
        allli = soup.find_all("li", {'class' : 'mb-2'})
        for litag in allli:
            licontents = litag.renderContents().decode('utf-8')
            licontents = self.__class__.htmltagPattern.sub("", licontents)
            licontents = licontents.replace("\n", " ").replace("\r", "")
            pps = re.search(provenancePattern, licontents)
            if pps:
                detailData['artwork_provenance'] = pps.groups()[0]
            lps = re.search(literaturePattern, licontents)
            if lps:
                detailData['artwork_literature'] = lps.groups()[0]
            eps = re.search(exhibitionPattern, licontents)
            if eps:
                detailData['artwork_exhibited'] = eps.groups()[0]
        alldatetimespan = soup.find_all("span", {'class' : 'dateTime'})
        detailData['auction_start_date'] = ""
        detailData['auction_house_name'] = "JOHN MORAN"
        if alldatetimespan.__len__() > 0:
            datetime = alldatetimespan[0].renderContents().decode('utf-8')
            datePattern = re.compile("(\w+\s+\d+,\s+\d{4})\s+")
            datetime = datetime.replace("\n", "").replace("\r", "")
            dps = re.search(datePattern, datetime)
            if dps:
                detailData['auction_start_date'] = dps.groups()[0]
                detailData['auction_start_date'] = self.__class__.formatDate(detailData['auction_start_date'])
        #if 'artwork_size_notes' in detailData.keys():
        #    detailData['artwork_size_notes'] = detailData['artwork_size_notes'].replace("H", "").replace("W", "").replace("Dia", "").replace("D", "")
        #imgtags = soup.find_all("img", {'class' : 'fbCarouselLargeImage'})
        imgtags = soup.find_all("a", {'data-zoom-id' : 'magicLotCarousel'})

        defaultimageurl = ""
        if imgtags.__len__() > 0:
            defaultimageurl = imgtags[0]['href']
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
        altimgdivPattern = re.compile("carousel\-mobile\-item")
        altdivtags = soup.find_all("div", {'class' : altimgdivPattern})
        alternateimgurls = []
        for altdiv in altdivtags:
            altimgtags = altdiv.find_all("img")
            altimgurl = altimgtags[0]['src']
            alternateimgurls.append(altimgurl)
        imgctr = 2
        if alternateimgurls.__len__() > 0:
            altimage2 = alternateimgurls[0]
            altimage2parts = altimage2.split("/")
            altimageurl = "/".join(altimage2parts[:-2])
            processedArtistName = artistname.replace(" ", "_")
            processedArtistName = unidecode.unidecode(processedArtistName)
            processedArtworkName = artworkname.replace(" ", "_")
            sublot_number = ""
            #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + self.saleno + "__" + lotno + "__" + sublot_number
            newname1 = self.saleno + "__" + processedArtistName + "__" + str(lotno) + "_b"
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
            #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + self.saleno + "__" + lotno + "__" + sublot_number
            newname1 = self.saleno + "__" + processedArtistName + "__" + str(lotno) + "_c"
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
            #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + self.saleno + "__" + lotno + "__" + sublot_number
            newname1 = self.saleno + "__" + processedArtistName + "__" + str(lotno) + "_d"
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
            #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + self.saleno + "__" + lotno + "__" + sublot_number
            newname1 = self.saleno + "__" + processedArtistName + "__" + str(lotno) + "_e"
            #encryptedFilename = self.encryptFilename(newname1)
            encryptedFilename = newname1
            detailData['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
            detailData['artwork_images' + str(imgctr)] = altimage2
        descdivtags = soup.find_all("div", {'id' : 'hoverZoomViewport'})
        if descdivtags.__len__() > 0:
            desccontents = descdivtags[0].renderContents().decode('utf-8')
            detailData['artwork_description'] = desccontents
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
            detailData['artwork_description'] = detailData['artwork_description'].replace('"', "'")
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
        baseUrl = "https://www.johnmoran.com"
        info = []
        endSpacePattern = re.compile("\s+$", re.DOTALL)
        beginspacePattern = re.compile("^\s+")
        yearPattern = re.compile("\d{4}")
        matcatdict_en = {}
        matcatdict_fr = {}
        #with open("docs/fineart_materials.csv", newline='') as mapfile:
        with open("/Users/saiswarupsahu/freelanceprojectchetan/docs/fineart_materials.csv", newline='') as mapfile:
            mapreader = csv.reader(mapfile, delimiter=",", quotechar='"')
            for maprow in mapreader:
                matcatdict_en[maprow[1]] = maprow[3]
                matcatdict_fr[maprow[2]] = maprow[3]
        mapfile.close()
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
            data['artist_name'] = ""
            data['artwork_name'] = ""
            data['artwork_measurements_height']="0"
            data['artwork_measurements_width']="0"
            data['artwork_measurements_depth']="0"
            anchorcontent = htmlanchor.renderContents().decode('utf-8')
            anchorcontent = anchorcontent.replace("\n", " ").replace("\r", " ")
            infoPattern1 = re.compile("(\d+):\s+([^,]+),\s+\(([\d\s\-b\.]+),\s+[\w\s\-,]+\),\s+\"([^\"]+)\",\s+([^,]+),\s+(.*)$", re.DOTALL)
            infoPattern1_1 = re.compile("(\d+):\s+([^,]+),\s+\(([\d\s\-b\.]+),\s+[\w\s\-,]+\),\s+([^,]+),\s+([^,]+),\s+([^,]+)", re.DOTALL)
            infoPattern2 = re.compile("(\d+):\s+([^,]+),\s+\(([\d\s\-b\.]+),\s+[\w\s\-,]+\),\s+\"([^\"]+)\"\s+(\d{4}),\s+([^,]+)\s+(.*)$", re.DOTALL)
            infoPattern2_1 = re.compile("(\d+):\s+([^,]+),\s+\(([\d\s\-b\.]+),\s+[\w\s\-,]+\),\s+\"([^\"]+)\"\s+circa\s+(\d{4}),\s+([^,]+),\s+(.*)$", re.DOTALL)
            infoPattern2_2 = re.compile("(\d+):\s+([^,]+),\s+\(([\d\s\-b\.]+),\s+[\w\s\-,]+\),\s+\"([^\"]+)\"\s+(\d{4}),\s+([^,]+),\s+(.*)$", re.DOTALL)
            infoPattern3 = re.compile("(\d+):\s+([^,]+),\s+\(([\d\s\-b\.]+),\s+[\w\s\-,]+\),\s+\"([^\"]+\"\s+\([^\)]+\))\s+(\d{4}),\s+(\d{4}),\s+([^,]+)\s*$", re.DOTALL)
            infoPattern4 = re.compile("(\d+):\s+([^,]+),\s+\(([\d\s\-b\.]+),\s+[\w\s\-,]+\),\s+\"([^\"]+\"\s+\([^\)]+\)),\s+(\d{4}),([^,]+)\s*$", re.DOTALL)
            infoPattern5 = re.compile("(\d+):\s+([^,]+),\s+\(([\d\s\w]+),\s+[\w\s\-,]+\),\s+([^,]+),\s+([^,]+),?\s*", re.DOTALL)
            infoPattern5_1 = re.compile("(\d+):\s+([^,]+),\s+\(([\d\s\-]+),\s+[\w\s\-,]+\),\s+([^,]+),\s+(\d{4}),\s+([^,]+),?\s*", re.DOTALL)
            infoPattern5_2 = re.compile("(\d+):\s+([^,]+),\s+\(([\d\s\-]+),\s+[\w\s\-,]+\),\s+(.*?),\s+(\d{4}),\s+([^,]+),?\s*", re.DOTALL)
            infoPattern5_3 = re.compile("(\d+):\s+([^\(]+)\s+\(([\d\s\-b\.]+),\s+[\w\s\-,]+\)", re.DOTALL)
            infoPattern5_4 = re.compile("(\d+):\s+([\w\s\(\)]+)\s+\(([\d\s\-b\.]+),\s+[\w\s\-,]+\)", re.DOTALL)
            infoPattern6 = re.compile("(\d+):\s+([^,]+),\s+\(([\d\s\w]+),\s+[\w\s\-,]+\),\s+\"([^\"]+),\"\s+(\d{4}),\s+([^\d]+),\s+(.*)$", re.DOTALL)
            infoPattern7 = re.compile("(\d+):\s+([\w\s\-]+)", re.DOTALL)
            bdPattern1 = re.compile("(\d{4})\s*\-\s*(\d{4})")
            bdPattern2 = re.compile("b\.\s*(\d{4})")
            sizePattern0 = re.compile("([\d\.]+)([a-zA-Z]{2})\s*H\s*x\s*([\d\.]+)([a-zA-Z]{2})\s*W\s*x\s*([\d\.]+)([a-zA-Z]{2})\s*D", re.IGNORECASE)
            sizePattern = re.compile("([\d\.]+\"\s+H\s+x\s+[\d\.]+\"\s+W)", re.IGNORECASE|re.DOTALL)
            sizePattern1 = re.compile("([\d\.]+)([a-zA-Z]{2})\s*H\s*x\s*([\d\.]+)([a-zA-Z]{2})\s*Dia", re.IGNORECASE|re.DOTALL)
            estimatePattern = re.compile("Estimate:\s+\$([\d,\.]+)\s+\-\s+\$([\d\.,]+)", re.DOTALL|re.IGNORECASE)
            soldPattern = re.compile("Sold:\s+\$([\d\.,]+)", re.DOTALL|re.IGNORECASE)
            centuryPattern = re.compile("century", re.IGNORECASE)
            measureunitPattern = re.compile("([a-zA-Z]{2})")
            bdPattern = re.compile("\d{4}")
            sizedata = re.compile("(?:\d+(?:\.\d*)?|\.\d+)")
            ips1 = re.search(infoPattern1, anchorcontent)
            ips1_1 = re.search(infoPattern1_1, anchorcontent)
            ips2 = re.search(infoPattern2, anchorcontent)
            ips2_1 = re.search(infoPattern2_1, anchorcontent)
            ips2_2 = re.search(infoPattern2_2, anchorcontent)
            ips3 = re.search(infoPattern3, anchorcontent)
            ips4 = re.search(infoPattern4, anchorcontent)
            ips5 = re.search(infoPattern5, anchorcontent)
            ips5_1 = re.search(infoPattern5_1, anchorcontent)
            ips5_2 = re.search(infoPattern5_2, anchorcontent)
            ips5_3 = re.search(infoPattern5_3, anchorcontent)
            ips5_4 = re.search(infoPattern5_4, anchorcontent)
            ips6 = re.search(infoPattern6, anchorcontent)
            ips7 = re.search(infoPattern7, anchorcontent)
            if ips1:
                ipsg1 = ips1.groups()
                lotno = ipsg1[0]
                artist = ipsg1[1]
                data['lot_num'] = lotno
                data['artist_name'] = artist
                birthyear, deathyear = "", ""
                birthdeath = ipsg1[2]
                if "-" in birthdeath:
                    bds1 = re.search(bdPattern1, birthdeath)
                    if bds1:
                        birthyear = bds1.groups()[0]
                        deathyear = bds1.groups()[1]
                        data['artist_birth'] = birthyear
                        data['artist_death'] = deathyear
                else:
                    bds2 = re.search(bdPattern2, birthdeath)
                    if bds2:
                        birthyear = bds2.groups()[0]
                        data['artist_birth'] = birthyear
                title = ipsg1[3]
                medium = ipsg1[4]
                size = ipsg1[5]
                data['artwork_name'] = title
                data['artwork_materials'] = medium
                zps = re.search(sizePattern, size)
                if zps:
                    data['artwork_size_notes'] = zps.groups()[0]
            elif ips1_1:
                ipsg1_1 = ips1_1.groups()
                lotno = ipsg1_1[0]
                artist = ipsg1_1[1]
                data['lot_num'] = lotno
                data['artist_name'] = artist
                birthyear, deathyear = "", ""
                birthdeath = ipsg1_1[2]
                if "-" in birthdeath:
                    bds1 = re.search(bdPattern1, birthdeath)
                    if bds1:
                        birthyear = bds1.groups()[0]
                        deathyear = bds1.groups()[1]
                        data['artist_birth'] = birthyear
                        data['artist_death'] = deathyear
                else:
                    bds2 = re.search(bdPattern2, birthdeath)
                    if bds2:
                        birthyear = bds2.groups()[0]
                        data['artist_birth'] = birthyear
                title = ipsg1_1[3]
                infobj = ipsg1_1[4]
                medium = ipsg1_1[5]
                data['artwork_name'] = title
                if re.search(yearPattern, infobj):
                    yearfrom = infobj
                    data['artwork_start_year'] = yearfrom
                    medium = ipsg1_1[5]
                else:
                    medium = infobj
                data['artwork_materials'] = medium
            elif ips2:
                ipsg2 = ips2.groups()
                lotno = ipsg2[0]
                artist = ipsg2[1]
                data['lot_num'] = lotno
                data['artist_name'] = artist
                birthyear, deathyear = "", ""
                birthdeath = ipsg2[2]
                if "-" in birthdeath:
                    bds1 = re.search(bdPattern1, birthdeath)
                    birthyear = bds1.groups()[0]
                    deathyear = bds1.groups()[1]
                    data['artist_birth'] = birthyear
                    data['artist_death'] = deathyear
                else:
                    bds2 = re.search(bdPattern2, birthdeath)
                    birthyear = bds2.groups()[0]
                    data['artist_birth'] = birthyear
                title = ipsg2[3]
                yearfrom = ipsg2[4]
                medium = ipsg2[5]
                data['artwork_name'] = title
                data['artwork_materials'] = medium
                data['artwork_start_year'] = yearfrom
            elif ips2_1:
                ipsg2_1 = ips2_1.groups()
                lotno = ipsg2_1[0]
                artist = ipsg2_1[1]
                data['lot_num'] = lotno
                data['artist_name'] = artist
                birthyear, deathyear = "", ""
                birthdeath = ipsg2_1[2]
                if "-" in birthdeath:
                    bds1 = re.search(bdPattern1, birthdeath)
                    birthyear = bds1.groups()[0]
                    deathyear = bds1.groups()[1]
                    data['artist_birth'] = birthyear
                    data['artist_death'] = deathyear
                else:
                    bds2 = re.search(bdPattern2, birthdeath)
                    birthyear = bds2.groups()[0]
                    data['artist_birth'] = birthyear
                title = ipsg2_1[3]
                yearfrom = ipsg2_1[4]
                medium = ipsg2_1[5]
                data['artwork_name'] = title
                data['artwork_materials'] = medium
                data['artwork_start_year'] = yearfrom
            elif ips2_2:
                ipsg2_2 = ips2_2.groups()
                lotno = ipsg2_2[0]
                artist = ipsg2_2[1]
                data['lot_num'] = lotno
                data['artist_name'] = artist
                birthyear, deathyear = "", ""
                birthdeath = ipsg2_2[2]
                if "-" in birthdeath:
                    bds1 = re.search(bdPattern1, birthdeath)
                    birthyear = bds1.groups()[0]
                    deathyear = bds1.groups()[1]
                    data['artist_birth'] = birthyear
                    data['artist_death'] = deathyear
                else:
                    bds2 = re.search(bdPattern2, birthdeath)
                    birthyear = bds2.groups()[0]
                    data['artist_birth'] = birthyear
                title = ipsg2_2[3]
                yearfrom = ipsg2_2[4]
                medium = ipsg2_2[5]
                data['artwork_name'] = title
                data['artwork_materials'] = medium
                data['artwork_start_year'] = yearfrom
            elif ips3:
                ipsg3 = ips3.groups()
                lotno = ipsg3[0]
                artist = ipsg3[1]
                data['lot_num'] = lotno
                data['artist_name'] = artist
                birthyear, deathyear = "", ""
                birthdeath = ipsg3[2]
                if "-" in birthdeath:
                    bds1 = re.search(bdPattern1, birthdeath)
                    birthyear = bds1.groups()[0]
                    deathyear = bds1.groups()[1]
                    data['artist_birth'] = birthyear
                    data['artist_death'] = deathyear
                else:
                    bds2 = re.search(bdPattern2, birthdeath)
                    birthyear = bds2.groups()[0]
                    data['artist_birth'] = birthyear
                title = ipsg3[3]
                yearfrom = ipsg3[4]
                yearto = ipsg3[5]
                medium = ipsg3[6]
                data['artwork_name'] = title
                data['artwork_materials'] = medium
                data['artwork_start_year'] = yearfrom
                data['artwork_end_year'] = yearto
            elif ips4:
                ipsg4 = ips4.groups()
                lotno = ipsg4[0]
                artist = ipsg4[1]
                data['lot_num'] = lotno
                data['artist_name'] = artist
                birthyear, deathyear = "", ""
                birthdeath = ipsg4[2]
                if "-" in birthdeath:
                    bds1 = re.search(bdPattern1, birthdeath)
                    birthyear = bds1.groups()[0]
                    deathyear = bds1.groups()[1]
                    data['artist_birth'] = birthyear
                    data['artist_death'] = deathyear
                else:
                    bds2 = re.search(bdPattern2, birthdeath)
                    birthyear = bds2.groups()[0]
                    data['artist_birth'] = birthyear
                title = ipsg4[3]
                yearfrom = ipsg4[4]
                medium = ipsg4[5]
                data['artwork_name'] = title
                data['artwork_materials'] = medium
                data['artwork_start_year'] = yearfrom
            elif ips5:
                ipsg5 = ips5.groups()
                lotno = ipsg5[0]
                artist = ipsg5[1]
                data['lot_num'] = lotno
                data['artist_name'] = artist
                birthyear, deathyear = "", ""
                birthdeath = ipsg5[2]
                data['artist_birth'] = birthdeath
                title = ipsg5[3]
                medium = ipsg5[4]
                data['artwork_name'] = title
                data['artwork_materials'] = medium
            elif ips5_1:
                ipsg5_1 = ips5_1.groups()
                lotno = ipsg5_1[0]
                artist = ipsg5_1[1]
                data['lot_num'] = lotno
                data['artist_name'] = artist
                birthyear, deathyear = "", ""
                birthdeath = ipsg5_1[2]
                if "-" in birthdeath:
                    bds1 = re.search(bdPattern1, birthdeath)
                    birthyear = bds1.groups()[0]
                    deathyear = bds1.groups()[1]
                    data['artist_birth'] = birthyear
                    data['artist_death'] = deathyear
                else:
                    bds2 = re.search(bdPattern2, birthdeath)
                    birthyear = bds2.groups()[0]
                    data['artist_birth'] = birthyear
                title = ipsg5_1[3]
                yearfrom = ipsg5_1[4]
                medium = ipsg5_1[5]
                data['artwork_name'] = title
                data['artwork_materials'] = medium
                data['artwork_start_year'] = yearfrom
            elif ips5_2:
                ipsg5_2 = ips5_2.groups()
                lotno = ipsg5_2[0]
                artist = ipsg5_2[1]
                data['lot_num'] = lotno
                data['artist_name'] = artist
                birthyear, deathyear = "", ""
                birthdeath = ipsg5_2[2]
                if "-" in birthdeath:
                    bds1 = re.search(bdPattern1, birthdeath)
                    birthyear = bds1.groups()[0]
                    deathyear = bds1.groups()[1]
                    data['artist_birth'] = birthyear
                    data['artist_death'] = deathyear
                else:
                    bds2 = re.search(bdPattern2, birthdeath)
                    birthyear = bds2.groups()[0]
                    data['artist_birth'] = birthyear
                title = ipsg5_2[3]
                yearfrom = ipsg5_2[4]
                medium = ipsg5_2[5]
                data['artwork_name'] = title
                data['artwork_materials'] = medium
                data['artwork_start_year'] = yearfrom
            elif ips5_3:
                ipsg5_3 = ips5_3.groups()
                lotno = ipsg5_3[0]
                artist = ipsg5_3[1]
                data['lot_num'] = lotno
                data['artist_name'] = artist
                birthyear, deathyear = "", ""
                birthdeath = ipsg5_3[2]
                if "-" in birthdeath:
                    bds1 = re.search(bdPattern1, birthdeath)
                    birthyear = bds1.groups()[0]
                    deathyear = bds1.groups()[1]
                    data['artist_birth'] = birthyear
                    data['artist_death'] = deathyear
                else:
                    bds2 = re.search(bdPattern2, birthdeath)
                    birthyear = bds2.groups()[0]
                    data['artist_birth'] = birthyear
            elif ips5_4:
                ipsg5_4 = ips5_4.groups()
                lotno = ipsg5_4[0]
                artist = ipsg5_4[1]
                data['lot_num'] = lotno
                data['artist_name'] = artist
                birthyear, deathyear = "", ""
                birthdeath = ipsg5_4[2]
                if "-" in birthdeath:
                    bds1 = re.search(bdPattern1, birthdeath)
                    birthyear = bds1.groups()[0]
                    deathyear = bds1.groups()[1]
                    data['artist_birth'] = birthyear
                    data['artist_death'] = deathyear
                else:
                    bds2 = re.search(bdPattern2, birthdeath)
                    birthyear = bds2.groups()[0]
                    data['artist_birth'] = birthyear
            elif ips6:
                ipsg6 = ips6.groups()
                lotno = ipsg6[0]
                artist = ipsg6[1]
                data['lot_num'] = lotno
                data['artist_name'] = artist
                birthyear, deathyear = "", ""
                birthdeath = ipsg6[2]
                data['artist_birth'] = birthdeath
                title = ipsg6[3]
                yearfrom = ipsg6[4]
                medium = ipsg6[5]
                data['artwork_name'] = title
                data['artwork_materials'] = medium
                data['artwork_start_year'] = yearfrom
            elif ips7:
                ipsg7 = ips7.groups()
                lotno = ipsg7[0]
                title = ipsg7[1]
                data['lot_num'] = lotno
                data['artist_name'] = ""
                birthyear, deathyear = "", ""
                data['artist_birth'] = birthyear
                data['artist_death'] = deathyear
                data['artwork_name'] = title
                data['artwork_materials'] = ""
                data['artwork_start_year'] = ""
            nextptag = htmldiv.findNext("p")
            pcontents = nextptag.renderContents().decode('utf-8')
            pcontents = pcontents.replace("\n", " ").replace("\r", " ")
            eps = re.search(estimatePattern, pcontents)
            if eps:
                low = eps.groups()[0]
                high = eps.groups()[1]
                #data['ESTIMATE'] = low + " - " + high + " USD"
                data['price_estimate_min'] = low
                data['price_estimate_max'] = high
            nextdivtag = nextptag.findNext("div")
            nextdivcontents = nextdivtag.renderContents().decode('utf-8')
            nextdivcontents = self.__class__.htmltagPattern.sub("", nextdivcontents)
            nextdivcontents = nextdivcontents.replace("\n", " ").replace("\r", " ")
            sps = re.search(soldPattern, nextdivcontents)
            if sps:
                soldprice = sps.groups()[0]
                data['price_sold'] = soldprice
            """
            if 'lot_num' not in data.keys():
                print(data['lot_origin_url'])
                continue
            print(data['lot_num'] + " ## " + data['artwork_name'] + " ## " + data['artist_birth'] + " ## " + data['price_estimate_min'] + " ## " + data['artwork_materials'])
            """
            print("Getting '%s'..."%data['lot_origin_url'])
            detailsPageContent = self.getDetailsPage(detailUrl)
            if not lotno:
                continue
            detailData = self.parseDetailPage(detailsPageContent, lotno, imagepath, data['artist_name'], data['artwork_name'], downloadimages)
            for k in detailData.keys():
                data[k] = detailData[k]
            if 'artwork_materials' in data.keys():
                if re.search(centuryPattern, data['artwork_materials']):
                    data['artwork_start_year'] = data['artwork_materials']
                    data['artwork_start_year'] = beginspacePattern.sub("", data['artwork_start_year'])
                    data['artwork_materials'] = ""
                elif re.search(bdPattern, data['artwork_materials']):
                    birthdeath = data['artwork_materials']
                    if "-" in birthdeath:
                        bds1 = re.search(bdPattern1, birthdeath)
                        if bds1:
                            birthyear = bds1.groups()[0]
                            deathyear = bds1.groups()[1]
                            data['artist_birth'] = birthyear
                            data['artist_death'] = deathyear
                    else:
                        bds2 = re.search(bdPattern2, birthdeath)
                        if bds2:
                            birthyear = bds2.groups()[0]
                            data['artist_birth'] = birthyear
                    data['artwork_materials'] = ""
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
            if 'artwork_materials' in data.keys():
                data['artwork_materials'] = beginspacePattern.sub("", data['artwork_materials'])
            if 'artwork_markings' in data.keys():
                data['artwork_markings'] = beginspacePattern.sub("", data['artwork_markings'])
            if 'artwork_size_notes' in data.keys():
                data['artwork_size_notes'] = beginspacePattern.sub("", data['artwork_size_notes'])
                sizeparts = detailData['artwork_size_notes'].split("x")
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
                zps0 = re.search(sizePattern0, detailData['artwork_size_notes'])
                zps = re.search(sizePattern, detailData['artwork_size_notes'])
                zps1 = re.search(sizePattern1, detailData['artwork_size_notes'])
                if zps0:
                    data['artwork_measurements_height'] = zps0.groups()[0]
                    data['artwork_measurements_width'] = zps0.groups()[2]
                    data['artwork_measurements_depth'] = zps0.groups()[4]
                    data['auction_measureunit'] = zps0.groups()[1]
                    data['artwork_measurements_height'] = beginspacePattern.sub("", data['artwork_measurements_height'])
                    data['artwork_measurements_width'] = beginspacePattern.sub("", data['artwork_measurements_width'])
                    data['artwork_measurements_depth'] = beginspacePattern.sub("", data['artwork_measurements_depth'])
                    
                elif zps:
                    data['artwork_measurements_height'] = zps.groups()[0]
                    data['artwork_measurements_width'] = zps.groups()[2]
                    data['auction_measureunit'] = zps.groups()[1]
                    data['artwork_measurements_height'] = beginspacePattern.sub("", data['artwork_measurements_height'])
                    data['artwork_measurements_width'] = beginspacePattern.sub("", data['artwork_measurements_width'])
                   
                elif zps1:
                    data['artwork_measurements_height'] = zps1.groups()[0]
                    data['artwork_measurements_depth'] = zps1.groups()[2]
                    data['auction_measureunit'] = zps1.groups()[1]
                    data['artwork_measurements_height'] = beginspacePattern.sub("", data['artwork_measurements_height'])
                    data['artwork_measurements_depth'] = beginspacePattern.sub("", data['artwork_measurements_depth'])
            try:
                data['artwork_measurements_height']="".join(re.findall("(?:\d+(?:\.\d*)?|\.\d+)",data['artwork_measurements_height']))
            except:
                pass
            try:
                data['artwork_measurements_width']="".join(re.findall("(?:\d+(?:\.\d*)?|\.\d+)",data['artwork_measurements_width']))
            except:
                pass
            try:
                data['artwork_measurements_depth']="".join(re.findall("(?:\d+(?:\.\d*)?|\.\d+)",data['artwork_measurements_depth']))
            except:
                pass

            data['artwork_size_notes']=data['artwork_measurements_height']+"x"+data['artwork_measurements_width']+"x"+data['artwork_measurements_depth'] +" "+"In"
                    
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
            data['auction_location'] = "Monrovia, CA"
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
    pageurl = "http://216.137.189.57:8080/scrapers/finish/?scrapername=Johnmoran&auctionnumber=%s&auctionurl=%s&scrapertype=2"%(auctionno, urllib.parse.quote(auctionurl))
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
    johnmoran = JohnMoranBot(auctionurl, auctionnumber)
    fp = open(csvpath, "w")
    fieldnames = ['auction_house_name', 'auction_location', 'auction_num', 'auction_start_date', 'auction_end_date', 'auction_name', 'lot_num', 'sublot_num', 'price_kind', 'price_estimate_min', 'price_estimate_max', 'price_sold', 'artist_name', 'artist_birth', 'artist_death', 'artist_nationality', 'artwork_name', 'artwork_year_identifier', 'artwork_start_year', 'artwork_end_year', 'artwork_materials', 'artwork_category', 'artwork_markings', 'artwork_edition', 'artwork_description', 'artwork_measurements_height', 'artwork_measurements_width', 'artwork_measurements_depth', 'artwork_size_notes', 'auction_measureunit', 'artwork_condition_in', 'artwork_provenance', 'artwork_exhibited', 'artwork_literature', 'artwork_images1', 'artwork_images2', 'artwork_images3', 'artwork_images4', 'artwork_images5', 'image1_name', 'image2_name', 'image3_name', 'image4_name', 'image5_name', 'lot_origin_url']
    fieldsstr = ",".join(fieldnames)
    fp.write(fieldsstr + "\n")
    pagectr = 1
    while True:
        soup = BeautifulSoup(johnmoran.currentPageContent, features="html.parser")
        lotsdata = johnmoran.getLotsFromPage()
        info = johnmoran.getInfoFromLotsData(lotsdata, imagepath, downloadimages)
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
            nextpageUrl = johnmoran.baseUrl[:-1] + nextpageanchors[0]['href']
            johnmoran.pageRequest = urllib.request.Request(nextpageUrl, headers=johnmoran.httpHeaders)
            try:
                johnmoran.pageResponse = johnmoran.opener.open(johnmoran.pageRequest)
            except:
                print("Couldn't find the page %s"%str(pagectr))
                break
            johnmoran.currentPageContent = johnmoran.__class__._decodeGzippedContent(johnmoran.getPageContent())
        else:
            break
    fp.close()
    updatestatus(auctionnumber, auctionurl)

# Example: python johnmoran.py    https://www.johnmoran.com/auction-catalog/Prints-%26-Multiples_VETPJQGUQW/    VETPJQGUQW   /Users/saiswarupsahu/freelanceprojectchetan/johnmoran_VETPJQGUQW.csv /Users/saiswarupsahu/freelanceprojectchetan/1-5TNCV9 0 0

# Example: python johnmoran.py https://www.johnmoran.com/auction-catalog/Prints-Multiples_P0OB6ZHYZL/ P0OB6ZHYZL /home/supmit/work/art2/johnmoran_P0OB6ZHYZL.csv /home/supmit/work/art2/images/johnmoran/P0OB6ZHYZL 0 0

# supmit


#
#
#
#p
#
#p
