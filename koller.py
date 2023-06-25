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
from hyper.contrib import HTTP20Adapter

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


class KollerBot(object):
    
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
        try:
            return(self.pageResponse.read())
        except:
            return("")

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
        #idPattern = re.compile("preTableArea_")
        titledivtags = soup.find_all("h1")
        if titledivtags.__len__() > 0:
            titlecontent = titledivtags[0].renderContents().decode('utf-8')
            titlecontent = self.__class__.htmltagPattern.sub("", titlecontent)
            titlecontent = titlecontent.replace("$('#FilterDataBox').html", "")
            titlecontent = titlecontent.replace("(", "").replace(")", "")
            titlecontent = titlecontent.replace('"', "")
            self.auctiontitle = titlecontent
        idPattern = re.compile("detail\d+", re.DOTALL)
        lotblocks = soup.find_all("div", {'id' : idPattern})
        #lotspans = soup.find_all("span", {'style' : 'font-weight:bold'})
        lotdict = {}
        lotPattern = re.compile("Lot\s+(\d+)", re.IGNORECASE|re.DOTALL)
        ctr = 0
        for lotblock in lotblocks:
            lotblockcontent = lotblock.renderContents().decode('utf-8')
            lps = re.search(lotPattern, lotblockcontent)
            if lps:
                lotno = lps.groups()[0]
                lotdict[lotno] = lotblocks[ctr]
                ctr += 1
        #print(lotdict.keys())
        return lotdict
        

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
        baseUrl = "https://www.kollerauktionen.ch"
        detailData = {}
        soup = BeautifulSoup(detailsPage, features="html.parser")
        mediumPattern = re.compile("(gold)|(silver)|(brass)|(bronze)|(wood)|(porcelain)|(marble)|(metal)|(steel)|(\s+iron\s+)|(glass)|(plexiglas)|(chromogenic)|(paper)|(canvas)|(masonite)|(newsprint)|(silkscreen)|(parchment)|(linen)|(inkjet)|(ink\s+jet)|(\s+ink)|(pigment)|(\stin\s)|(photogravure)|(^oil\s+)|(\s+panel\s+)|(terracotta)|(ivory)|(\s+oak\s+)|(^oak\s+)|(\s+oak$)|(alabaster)|(chalk)|(gouache)|(watercolou?r)|(cardboard)", re.DOTALL|re.IGNORECASE)
        nonenglishmediumPattern = re.compile("(crayon)|(encre)|(plume)|(plume\s+et\s+encre)|(papier)|(pastel)|(craie)|(gouachée)|(aquarelle)|(lithographique)|(plomb)|(huile)|(cuivre)|(toile)|(bronze)|(Plâtre)|(en\s+terre\s+de\s+faïence)|(Öl)|(holz)|(tempera)|(kupfer)|(leinwand)", re.IGNORECASE|re.DOTALL)
        soldforPattern = re.compile("Sold\s+for\s+CHF\s+([\d\s,\.]+)\s+", re.IGNORECASE|re.DOTALL)
        editionPattern = re.compile("edition", re.IGNORECASE)
        editionnumberPattern = re.compile("(\d{1,3})\/\d{1,4}", re.DOTALL)
        crPattern = re.compile("Catalogue\s+raisonné", re.IGNORECASE|re.DOTALL)
        literaturePattern = re.compile("Literature\:", re.IGNORECASE|re.DOTALL)
        provenancePattern = re.compile("Provenance\:", re.IGNORECASE|re.DOTALL)
        exhibitionPattern = re.compile("Exhibition\:", re.IGNORECASE|re.DOTALL)
        sizePattern = re.compile("([\d,\.]+\s*x\s*[\d\.,]+)")
        sizePattern2 = re.compile("([\d,\.]+\s+cm)")
        datePattern = re.compile("(\d{2}\.\s+\w+\s+\d{4})\,", re.DOTALL)
        beginspacePattern = re.compile("^\s+")
        beginhyphenPattern = re.compile("^\s*\-\s*")
        enddigitPattern = re.compile("\d+\s*$", re.DOTALL)
        matcatdict_en = {}
        matcatdict_fr = {}
        with open("docs/fineart_materials.csv", newline='') as mapfile:
        #with open("/root/artwork/deploydirnew/docs/fineart_materials.csv", newline='') as mapfile:
            mapreader = csv.reader(mapfile, delimiter=",", quotechar='"')
            for maprow in mapreader:
                matcatdict_en[maprow[1]] = maprow[3]
                matcatdict_fr[maprow[2]] = maprow[3]
        mapfile.close()
        detailsectiontags = soup.find_all("section", {'class' : 'details'})
        if detailsectiontags.__len__() > 0:
            allparatags = detailsectiontags[0].find_all("p")
            for para in allparatags:
                paracontent = para.renderContents().decode("utf-8")
                ads = re.search(datePattern, paracontent)
                if ads and 'auction_start_date' not in detailData.keys():
                    auctiondate = ads.groups()[0]
                    auctiondate = auctiondate.replace(".", "")
                    detailData['auction_start_date'] = self.__class__.formatDate(auctiondate)
                    break
            alldivtags = detailsectiontags[0].find_all("div")
            for divtag in alldivtags:
                divcontents = divtag.renderContents().decode("utf-8")
                mps = re.search(mediumPattern, divcontents)
                if mps:
                    divparts = divcontents.split(".")
                    for divpart in divparts:
                        mps2 = re.search(mediumPattern, divpart)
                        if mps2 and 'artwork_materials' not in detailData.keys():
                            detailData['artwork_materials'] = divpart
                            detailData['artwork_materials'] = beginspacePattern.sub("", detailData['artwork_materials'])
                            detailData['artwork_materials'] = detailData['artwork_materials'].replace("&#215;", "x")
                            detailData['artwork_materials'] = detailData['artwork_materials'].replace("×", "x")
                            detailData['artwork_materials'] = self.__class__.htmltagPattern.sub("", detailData['artwork_materials'])
                            detailData['artwork_materials'] = detailData['artwork_materials'].replace('"', "'")
                            detailData['artwork_materials'] = sizePattern.sub("", detailData['artwork_materials'])
                            detailData['artwork_materials'] = sizePattern2.sub("", detailData['artwork_materials'])
                            detailData['artwork_materials'] = detailData['artwork_materials'].replace(" cm", "")
                            detailData['artwork_materials'] = beginspacePattern.sub("", detailData['artwork_materials'])
                            detailData['artwork_materials'] = enddigitPattern.sub("", detailData['artwork_materials'])
                nemps = re.search(nonenglishmediumPattern, divcontents)
                if nemps and 'artwork_materials' not in detailData.keys():
                    divparts = divcontents.split(".")
                    for divpart in divparts:
                        nemps2 = re.search(nonenglishmediumPattern, divpart)
                        if nemps2 and 'artwork_materials' not in detailData.keys():
                            detailData['artwork_materials'] = divpart
                            detailData['artwork_materials'] = beginspacePattern.sub("", detailData['artwork_materials'])
                            detailData['artwork_materials'] = detailData['artwork_materials'].replace("&#215;", "x")
                            detailData['artwork_materials'] = detailData['artwork_materials'].replace("×", "x")
                            detailData['artwork_materials'] = self.__class__.htmltagPattern.sub("", detailData['artwork_materials'])
                            detailData['artwork_materials'] = detailData['artwork_materials'].replace('"', "'")
                            detailData['artwork_materials'] = sizePattern.sub("", detailData['artwork_materials'])
                            detailData['artwork_materials'] = sizePattern2.sub("", detailData['artwork_materials'])
                            detailData['artwork_materials'] = detailData['artwork_materials'].replace(" cm", "")
                            detailData['artwork_materials'] = beginspacePattern.sub("", detailData['artwork_materials'])
                            detailData['artwork_materials'] = enddigitPattern.sub("", detailData['artwork_materials'])
                lps = re.search(literaturePattern, divcontents)
                if lps:
                    divparts = re.split("<br\s?\/?>", divcontents)
                    for divpart in divparts:
                        lps2 = re.search(literaturePattern, divpart)
                        if lps2 and 'artwork_literature' not in detailData.keys():
                            detailData['artwork_literature'] = divpart
                            detailData['artwork_literature'] = self.__class__.htmltagPattern.sub("", detailData['artwork_literature'])
                            detailData['artwork_literature'] = detailData['artwork_literature'].replace("Literature:", "")
                            detailData['artwork_literature'] = beginspacePattern.sub("", detailData['artwork_literature'])
                            detailData['artwork_literature'] = detailData['artwork_literature'].replace('"', "'")
                """
                eps = re.search(editionPattern, divcontents)
                if eps:
                    divparts = divcontents.split(".")
                    for divpart in divparts:
                        eps2 = re.search(editionPattern, divpart)
                        if eps2 and 'artwork_edition' not in detailData.keys():
                            detailData['artwork_edition'] = divpart
                            detailData['artwork_edition'] = beginspacePattern.sub("", detailData['artwork_edition'])
                            detailData['artwork_edition'] = self.__class__.htmltagPattern.sub("", detailData['artwork_edition'])
                            detailData['artwork_edition'] = detailData['artwork_edition'].replace('"', "'")
                """
                enps = re.search(editionnumberPattern, divcontents)
                if enps:
                    divparts = divcontents.split(".")
                    for divpart in divparts:
                        enps2 = re.search(editionnumberPattern, divpart)
                        if enps2 and 'artwork_edition' not in detailData.keys():
                            detailData['artwork_edition'] = enps2.groups()[0]
                            detailData['artwork_edition'] = beginspacePattern.sub("", detailData['artwork_edition'])
                pps = re.search(provenancePattern, divcontents)
                if pps:
                    divparts = re.split("<br\s?\/?><br\s?\/?>", divcontents)
                    for divpart in divparts:
                        pps2 = re.search(provenancePattern, divpart)
                        if pps2 and 'artwork_provenance' not in detailData.keys():
                            detailData['artwork_provenance'] = divpart
                            detailData['artwork_provenance'] = beginspacePattern.sub("", detailData['artwork_provenance'])
                            detailData['artwork_provenance'] = self.__class__.htmltagPattern.sub("", detailData['artwork_provenance'])
                            detailData['artwork_provenance'] = detailData['artwork_provenance'].replace('"', "'")
                            detailData['artwork_provenance'] = detailData['artwork_provenance'].replace('Provenance:', "")
                            detailData['artwork_provenance'] = beginhyphenPattern.sub("", detailData['artwork_provenance'])
                xps = re.search(exhibitionPattern, divcontents)
                if xps:
                    divparts = re.split("<br\s?\/?><br\s?\/?>", divcontents)
                    for divpart in divparts:
                        pps2 = re.search(provenancePattern, divpart)
                        if pps2 and 'artwork_exhibited' not in detailData.keys():
                            detailData['artwork_exhibited'] = divpart
                            detailData['artwork_exhibited'] = beginspacePattern.sub("", detailData['artwork_exhibited'])
                            detailData['artwork_exhibited'] = self.__class__.htmltagPattern.sub("", detailData['artwork_exhibited'])
                            detailData['artwork_exhibited'] = detailData['artwork_exhibited'].replace('"', "'")
                            detailData['artwork_exhibited'] = detailData['artwork_exhibited'].replace('Exhibition:', "")
                            detailData['artwork_exhibited'] = beginhyphenPattern.sub("", detailData['artwork_exhibited'])
        sfps = re.search(soldforPattern, detailsPage)
        if sfps and 'price_sold' not in detailData.keys():
            soldprice = sfps.groups()[0]
            soldprice = soldprice.replace("\n", "").replace("\r", "")
            soldprice = soldprice.replace(" ", "").replace("\t", "")
            detailData['price_sold'] = soldprice
        imagesectiontags = soup.find_all("section", {'class' : 'image-slide'})
        if imagesectiontags.__len__() > 0:
            imgtags = imagesectiontags[0].find_all("img")
            defaultimageurl = ""
            if imgtags.__len__() > 0:
                try:
                    defaultimageurl = self.baseUrl[:-1] + imgtags[0]['data-large-image']
                except:
                    print("Error: %s"%sys.exc_info()[1].__str__())
                    defaultimageurl = self.baseUrl[:-1] + imgtags[0]['src']
                #print(defaultimageurl)
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
            altimages = []
            for ictr in range(1, imgtags.__len__()):
                altimg = imgtags[ictr]['src']
                altimages.append(altimg)
            imgctr = 2
            if altimages.__len__() > 0:
                altimage2 = altimages[0]
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
            if altimages.__len__() > 1:
                altimage2 = altimages[1]
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
            if altimages.__len__() > 2:
                altimage2 = altimages[2]
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
            if altimages.__len__() > 3:
                altimage2 = altimages[3]
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
        detailssectiontags = soup.find_all("section", {'class' : 'details'})
        if detailssectiontags.__len__() > 0:
            sectioncontents = detailssectiontags[0].renderContents().decode('utf-8')
            sectioncontents = sectioncontents.replace("\n", "").replace("\r", "")
            sectioncontents = self.__class__.htmltagPattern.sub("", sectioncontents)
            detailData['artwork_description'] = sectioncontents
            detailData['artwork_description'] = detailData['artwork_description'].strip()
            detailData['artwork_description'] = detailData['artwork_description'].replace('"', "'")
            detailData['artwork_description'] = detailData['artwork_description'].replace("PROVENANCE", "<br><strong>Provenance</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("LITERATURE", "<br><strong>Literature</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("EXHIBITED", "<br><strong>Exhibited</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("EXPOSITIONS", "<br><strong>Expositions</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("BIBLIOGRAPHIE", "<br><strong>Literature</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("Condition Report", "<br><strong>Condition Report</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("Notes:", "<br><strong>Notes:</strong><br>")
            detailData['artwork_description'] = "<strong><br>Description<br></strong>" + detailData['artwork_description']
        return detailData


    def getImage(self, imageUrl, imagepath, downloadimages):
        imageUrlParts = imageUrl.split("/")
        imagefilename = imageUrlParts[-2] + "_" + imageUrlParts[-1]
        imagedir = imageUrlParts[-2]
        pps = re.search(partialUrlPattern, imageUrl)
        imgheaders = {}
        for k in self.httpHeaders.keys():
            imgheaders[k] = self.httpHeaders[k]
        imgheaders['sec-fetch-site'] = "none"
        imgheaders['Host'] = "www.kollerauktionen.ch"
        imgheaders['pragma'] = "no-cache"
        imgheaders['Accept'] = "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
        imgheaders['cache-control'] = "no-cache"
        imgheaders['Connection'] = "keep-alive"
        imgheaders['Accept-Language'] = "en-US,en;q=0.5"
        imgheaders['Accept-Encoding'] = "gzip,deflate"
        imgheaders['TE'] = "trailers"
        imgheaders.pop("Keep-Alive", None)
        if pps:
            imageUrl = self.baseUrl + imageUrl
        if downloadimages == "1":
            pageRequest = urllib.request.Request(imageUrl, headers=imgheaders)
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


    def getInfoFromLotsData(self, htmldict, imagepath, downloadimages):
        baseUrl = "https://www.kollerauktionen.ch"
        info = []
        beginspacePattern = re.compile("^\s+", re.DOTALL)
        endspacePattern = re.compile("\s+$")
        enddotPattern = re.compile("\.\s*$", re.DOTALL)
        measureunitPattern = re.compile("([a-zA-Z]{2})")
        for lotno in htmldict.keys():
            htmldiv = htmldict[lotno]
            data = {}
            data['auction_num'] = self.saleno
            data['lot_num'] = lotno
            data['artist_name'], data['artist_birth'], data['artist_death'], data['artwork_size_notes'], data['artwork_markings'], data['price_estimate_min'], data['price_estimate_max'], data['artwork_name'], data['artwork_start_year'], data['artwork_name'] = "", "", "", "", "", "", "", "", "", ""
            htmlContent = htmldiv.renderContents().decode('utf-8')
            s = BeautifulSoup(htmlContent, features="html.parser")
            allanchors = s.find_all("a")
            htmlanchor = allanchors[0]
            detailUrl = baseUrl + htmlanchor['href']
            data['lot_origin_url'] = detailUrl
            #dotdivtags = s.find_all("div", {'class' : 'dotdot'})
            h3tag = s.find("h3", {'class' : 'mt--0'})
            #if dotdivtags.__len__() > 0:
            if h3tag is not None:
                nextdiv = h3tag.findNext("div")
                alldivs = nextdiv.find_all("div") # All div tags included in  nextdiv are queried
                data['artist_name'] = h3tag.renderContents().decode('utf-8')
                data['artist_name'] = beginspacePattern.sub("", data['artist_name'])
                data['artist_name'] = endspacePattern.sub("", data['artist_name'])
                artistinfo = alldivs[0].renderContents().decode('utf-8')
                birthdeathPattern = re.compile("(\d{4})\s*\-?\s*(\d{0,4})", re.DOTALL)
                bdpset = re.findall(birthdeathPattern, artistinfo)
                if bdpset.__len__() > 0:
                    data['artist_birth'] = bdpset[0][0]
                if bdpset.__len__() > 1:
                    data['artist_death'] = bdpset[1][0]
                if alldivs.__len__() > 1:
                    data['artwork_name'] = alldivs[1].renderContents().decode('utf-8')
                    fromyearPattern = re.compile("(\d{4})")
                    fyps = re.search(fromyearPattern, data['artwork_name'])
                    if fyps:
                        data['artwork_start_year'] = fyps.groups()[0]
                        data['artwork_name'] = fromyearPattern.sub("", data['artwork_name'])
                    data['artwork_name'] = enddotPattern.sub("", data['artwork_name'])
                    data['artwork_name'] = data['artwork_name'].replace('"', "'")
                sizePattern = re.compile("([\d,\.x×\s&#;]+\s+cm)")
                sizePattern2 = re.compile("([\d\.,]+\s*\&#215;\s*[\d\.,]+\s+cm)")
                signPattern = re.compile("(signed)|(stamped)", re.IGNORECASE|re.DOTALL)
                for i in range(2, alldivs.__len__()):
                    divcontent = alldivs[i].renderContents().decode('utf-8')
                    zps = re.search(sizePattern, divcontent)
                    zps2 = re.search(sizePattern2, divcontent)
                    if zps and data['artwork_size_notes'] == "":
                        data['artwork_size_notes'] = zps.groups()[0]
                        data['artwork_size_notes'] = data['artwork_size_notes'].replace("&#215;", "x")
                        data['artwork_size_notes'] = data['artwork_size_notes'].replace("×", "x")
                        data['artwork_size_notes'] = beginspacePattern.sub("", data['artwork_size_notes'])
                        data['artwork_size_notes'] = data['artwork_size_notes'].replace(",", ".")
                        sizeparts = data['artwork_size_notes'].split("x")
                        data['artwork_measurements_height'] = sizeparts[0]
                        if sizeparts.__len__() > 1:
                            data['artwork_measurements_width'] = sizeparts[1]
                            mups = re.search(measureunitPattern, data['artwork_measurements_width'])
                            if mups:
                                data['auction_measureunit'] = mups.groups()[0]
                                data['artwork_measurements_width'] = measureunitPattern.sub("", data['artwork_measurements_width'])
                        if sizeparts.__len__() > 2:
                            data['artwork_measurements_depth'] = sizeparts[2]
                            mups = re.search(measureunitPattern, data['artwork_measurements_depth'])
                            if mups:
                                data['auction_measureunit'] = mups.groups()[0]
                                data['artwork_measurements_depth'] = measureunitPattern.sub("", data['artwork_measurements_depth'])
                    elif zps2 and data['artwork_size_notes'] == "":
                        data['artwork_size_notes'] = zps2.groups()[0]
                        data['artwork_size_notes'] = data['artwork_size_notes'].replace("&#215;", "x")
                        data['artwork_size_notes'] = data['artwork_size_notes'].replace("×", "x")
                        data['artwork_size_notes'] = beginspacePattern.sub("", data['artwork_size_notes'])
                        data['artwork_size_notes'] = data['artwork_size_notes'].replace(",", ".")
                        sizeparts = data['artwork_size_notes'].split("x")
                        data['artwork_measurements_height'] = sizeparts[0]
                        if sizeparts.__len__() > 1:
                            data['artwork_measurements_width'] = sizeparts[1]
                            mups = re.search(measureunitPattern, data['artwork_measurements_width'])
                            if mups:
                                data['auction_measureunit'] = mups.groups()[0]
                                data['artwork_measurements_width'] = measureunitPattern.sub("", data['artwork_measurements_width'])
                                data['artwork_measurements_depth'] = ""
                    divcontent = divcontent.split(".")
                    for para in divcontent:
                        para = para.replace('"', "'")
                        para = para.replace('\n', " ").replace("\r", " ")
                        sps = re.search(signPattern, para)
                        if sps and data['artwork_markings'] == "":
                            data['artwork_markings'] = para
                            data['artwork_markings'] = beginspacePattern.sub("", data['artwork_markings'])
                            data['artwork_markings'] = data['artwork_markings'].replace('"', "'")
            mainparatags = s.find_all("p")
            estimatePattern = re.compile("(\w{3})\s+([\d\s]+\/[\d\s]+)\s+\|", re.DOTALL)
            for mainpara in mainparatags:
                maincontent = mainpara.renderContents().decode('utf-8')
                eps = re.search(estimatePattern, maincontent)
                if eps and data['price_estimate_min'] == "":
                    epsg = eps.groups()
                    currency = epsg[0]
                    lowhigh = epsg[1]
                    lowhighparts = lowhigh.split("/")
                    low, high = "", ""
                    if lowhighparts.__len__() > 0:
                        low = lowhighparts[0]
                    if lowhighparts.__len__() > 1:
                        high = lowhighparts[1]
                    high = beginspacePattern.sub("", high)
                    if low != "":
                        data['price_estimate_min'] = low
                    if high != "":
                        data['price_estimate_max'] = high
            print("Getting '%s'..."%detailUrl)
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
            data['auction_house_name'] = "KOLLER"
            data['auction_name'] = self.auctiontitle
            data['auction_location'] = "Zurich"
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
    pageurl = "http://216.137.189.57:8080/scrapers/finish/?scrapername=Koller&auctionnumber=%s&auctionurl=%s&scrapertype=2"%(auctionno, urllib.parse.quote(auctionurl))
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
    koller = KollerBot(auctionurl, auctionnumber)
    fp = open(csvpath, "w")
    fieldnames = ['auction_house_name', 'auction_location', 'auction_num', 'auction_start_date', 'auction_end_date', 'auction_name', 'lot_num', 'sublot_num', 'price_kind', 'price_estimate_min', 'price_estimate_max', 'price_sold', 'artist_name', 'artist_birth', 'artist_death', 'artist_nationality', 'artwork_name', 'artwork_year_identifier', 'artwork_start_year', 'artwork_end_year', 'artwork_materials', 'artwork_category', 'artwork_markings', 'artwork_edition', 'artwork_description', 'artwork_measurements_height', 'artwork_measurements_width', 'artwork_measurements_depth', 'artwork_size_notes', 'auction_measureunit', 'artwork_condition_in', 'artwork_provenance', 'artwork_exhibited', 'artwork_literature', 'artwork_images1', 'artwork_images2', 'artwork_images3', 'artwork_images4', 'artwork_images5', 'image1_name', 'image2_name', 'image3_name', 'image4_name', 'image5_name', 'lot_origin_url']
    fieldsstr = ",".join(fieldnames)
    fp.write(fieldsstr + "\n")
    pagectr = 0
    chunksize = 1
    koller.httpHeaders['Referer'] = auctionurl
    soup = BeautifulSoup(koller.currentPageContent, features="html.parser")
    while True:
        lotsdata = koller.getLotsFromPage()
        if lotsdata.__len__() == 0:
            break
        info = koller.getInfoFromLotsData(lotsdata, imagepath, downloadimages)
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
        nextpageUrl = auctionurl + "?pposKatalogPosition=" + str( chunksize + 1)
        nextpagepath = nextpageUrl.replace("https://www.kollerauktionen.ch", "")
        print("NEXT PAGE URL: %s"%nextpageUrl)
        headers2 = {
        "User-Agent": "Supriyo",
        "referer": auctionurl,
        "cookie" : "CookieUsageConfirmed=true;Session=W_P__024VumtDZYwTq2MXgPqH1b07w==Gva+WRl5jLHwLO5e5Js6/trI19vwLCUJi4S39lGfMnbSQ7QJm6ilgCTvAs8hivrl; SecurityKey=615F44;ASP.NET_SessionId=2f02ecaa0yvzlfsoe25qihub;",
        "accept" : "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "accept-encoding" : "gzip,deflate",
        "accept-language" : "en-GB,en-US;q=0.9,en;q=0.8",
        "cache-control" : "max-age=0",
        "upgrade-insecure-requests" : "1",
        "sec-fetch-dest" : "document",
        "sec-fetch-mode" : "navigate",
        "sec-fetch-site" : "same-origin",
        "sec-fetch-user" : "?1",
        "sec-ch-ua" : "\".Not/A)Brand\";v=\"99\",\"Google Chrome\";v=\"103\",\"Chromium\";v=\"103\"",
        "sec-ch-ua-mobile" : "?0",
        "sec-ch-ua-platform" : "\"Linux\"",
        }
        sessions=requests.session()
        sessions.mount('https://', HTTP20Adapter())
        try:
            r=sessions.get(nextpageUrl, headers=headers2)
        except:
            print("Couldn't find the page %s"%str(pagectr))
            print("Error: %s"%sys.exc_info()[1].__str__())
            break
        koller.currentPageContent = r.text
        #print(koller.currentPageContent)
        soup = BeautifulSoup(koller.currentPageContent, features="html.parser")
        koller.httpHeaders['Referer'] = nextpageUrl
    fp.close()
    updatestatus(auctionnumber, auctionurl)

# Example: python koller.py "https://www.kollerauktionen.ch/en/zuerich/a191/prints-_-multiples-8/" A191E   /Users/saiswarupsahu/freelanceprojectchetan/koller_A191E.csv /home/supmit/work/art2/images/koller/a201 0 0


