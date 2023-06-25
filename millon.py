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
import csv
import unidecode
from socket import timeout

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


class MillonBot(object):
    
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
        self.httpHeaders = { 'User-Agent' : r'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36',  'Accept' : 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9', 'Accept-Language' : 'en-us,en;q=0.5', 'Accept-Encoding' : 'gzip,deflate', 'Accept-Charset' : 'ISO-8859-1,utf-8;q=0.7,*;q=0.7', 'Connection' : 'keep-alive', }
        self.httpHeaders['cache-control'] = "max-age=0"
        self.httpHeaders['sec-ch-ua'] = "\".Not/A)Brand\";v=\"99\", \"Google Chrome\";v=\"103\", \"Chromium\";v=\"103\""
        self.httpHeaders['sec-ch-ua-mobile'] = "?0"
        self.httpHeaders['sec-ch-ua-platform'] = "Linux"
        self.httpHeaders['upgrade-insecure-requests'] = "1"
        self.httpHeaders['sec-fetch-dest'] = "document"
        self.httpHeaders['sec-fetch-mode'] = "navigate"
        self.httpHeaders['sec-fetch-site'] = "none"
        self.httpHeaders['sec-fetch-user'] = "?1"
        self.homeDir = os.getcwd()
        self.auctionurl = auctionurl
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
        self.lastlotnumber = 0


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
        datestrcomponents = datestr.split(" ")
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
        
        titletag = soup.find("title")
        millonPattern = re.compile("\s+\|\s+Millon", re.IGNORECASE|re.DOTALL)
        if titletag is not None:
            self.auctiontitle = titletag.renderContents().decode('utf-8')
            self.auctiontitle = self.auctiontitle.replace("\n", "").replace("\r", "")
            self.auctiontitle = millonPattern.sub("", self.auctiontitle)
        cardbodyPattern = re.compile("card\-body\s+", re.DOTALL)
        lotdivtags = soup.find_all("div", {'class' : cardbodyPattern})
        lotbodies = []
        for lotdiv in lotdivtags:
            lotspantag = lotdiv.find("span", {'class' : 'category'})
            if lotspantag is not None:
                lotbodies.append(lotdiv)
        dateh2tag = soup.find("h2", {'class' : 'thiner text-center'})
        if dateh2tag is not None:
            datecontent = dateh2tag.renderContents().decode('utf-8')
            datecontent = datecontent.replace("\n", "").replace("\r", "")
            datePattern = re.compile("(\d{1,2}\s+[^\d\s]+\s+\d{4})")
            dps = re.search(datePattern, datecontent)
            if dps:
                self.auctiondate = dps.groups()[0]
        return lotbodies
        

    def getDetailsPage(self, detailUrl):
        self.requestUrl = detailUrl
        #self.pageRequest = urllib.request.Request(self.requestUrl, headers=self.httpHeaders)
        self.pageResponse = None
        self.postData = {}
        try:
            #self.pageResponse = self.opener.open(self.pageRequest, timeout=10)
            response = requests.get(self.requestUrl, headers=self.httpHeaders, timeout=10)
            #headers = self.pageResponse.getheaders()
        except:
            print ("Couldn't fetch page due to limited connectivity. Please check your internet connection and try again. %s"%sys.exc_info()[1].__str__())
            return ""
        #self.currentPageContent = self.__class__._decodeGzippedContent(self.getPageContent())
        self.currentPageContent = response.text
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
        baseUrl = "https://www.millon.com"
        detailData = {}
        brPattern = re.compile("<br\s*\/?>")
        beginspacePattern = re.compile("^\s+")
        endspacePattern = re.compile("\s+$")
        endcommaPattern = re.compile(",\s*$")
        literaturePattern = re.compile("Bibliographie", re.IGNORECASE|re.DOTALL)
        provenancePattern = re.compile("PROVENANCE", re.IGNORECASE|re.DOTALL)
        editionPattern = re.compile("(es\.\s+\d+\/\d+)", re.IGNORECASE|re.DOTALL)
        sizePattern1 = re.compile("([\d\sx\.,]+)\s+(cm)", re.DOTALL)
        sizePattern2 = re.compile("([\d\sx\.,]+)\s+(in)", re.DOTALL)
        sizePattern3 = re.compile("([\d\sx\.,\/]+)\s+(cm)", re.DOTALL)
        sizePattern4 = re.compile("([\d\sx\.,\/]+)\s+(in)", re.DOTALL)
        mediumPattern = re.compile("(gold)|(silver)|(brass)|(bronze)|(wood)|(porcelain)|(stone)|(marble)|(metal)|(steel)|(iron)|(glass)|(plexiglas)|(chromogenic)|(paper)|(canvas)|(masonite)|(newsprint)|(silkscreen)|(parchment)|(linen)|(inkjet)|(ink\s+jet)|(pigment)|(\stin\s)|(photogravure)|(^oil\s+)|(\s+panel\s+)|(terracotta)|(ivory)|(\s+oak\s+)|(^oak\s+)|(\s+oak$)|(alabaster)|(\s+ink\s+)|(pencil)|(albumen)|(oil\s+)|(\s+oil)|(panel)|(acrylic)|(print)|(Huile)|(toile)|(plume)|(encre)|(lavis)|(Gravure)|(Pierre)|(pastel)|(panneau)|(Sanguine)|(Crayon)|(aquarelle)|(papier)", re.DOTALL|re.IGNORECASE)
        signedPattern = re.compile("(signé[^\.]+)[\.,\w\s;]*$")
        yearPattern = re.compile("(\d{4})")
        measureunitPattern = re.compile("\s([a-zA-Z]{2})\.?")
        dotPattern = re.compile("\w+\.[\s\w]+", re.DOTALL)
        soup = BeautifulSoup(detailsPage, features="html.parser")
        estimatetag = soup.find("span", {'class' : 'push'})
        if estimatetag:
            estimatecontents = estimatetag.renderContents().decode('utf-8')
            estimatecontents = estimatecontents.replace("\n", "").replace("\r", "")
            estimatecontents = beginspacePattern.sub("", estimatecontents)
            estimatecontents = endspacePattern.sub("", estimatecontents)
            estimatecontents = estimatecontents.replace("€", "")
            estimateparts = estimatecontents.split("-")
            detailData['price_estimate_min'] = estimateparts[0]
            if estimateparts.__len__() > 1:
                detailData['price_estimate_max'] = estimateparts[1]
        descdivtags = soup.find_all("div", {'class' : 'card-body'})
        if descdivtags.__len__() > 0:
            descdivtag = descdivtags[0]
        else:
            descdivtag = None
        #print(descdivtag)
        if descdivtag is not None:
            desccontents = descdivtag.renderContents().decode('utf-8')
            descparts = desccontents.split("\n")
            desccontents = desccontents.replace("\n", "").replace("\r", "")
            desccontents = self.__class__.htmltagPattern.sub("", desccontents)
            #print(desccontents)
            zps1 = re.search(sizePattern1, desccontents)
            zps2 = re.search(sizePattern2, desccontents)
            zps3 = re.search(sizePattern3, desccontents)
            zps4 = re.search(sizePattern4, desccontents)
            if zps1:
                detailData['artwork_size_notes'] = zps1.groups()[0]
            elif zps2:
                detailData['artwork_size_notes'] = zps2.groups()[0]
            elif zps3:
                detailData['artwork_size_notes'] = zps3.groups()[0]
            elif zps4:
                detailData['artwork_size_notes'] = zps4.groups()[0]
            detailData['artwork_description'] = desccontents
            dctr = 0
            for dpart in descparts:
                dpart = dpart.replace("\n", "").replace("\r", "")
                dpart = self.__class__.htmltagPattern.sub("", dpart)
                dpart = beginspacePattern.sub("", dpart)
                mps = re.search(mediumPattern, dpart)
                yps = re.search(yearPattern, dpart)
                sps = re.search(signedPattern, dpart)
                pps = re.search(provenancePattern, dpart)
                lps = re.search(literaturePattern, dpart)
                if mps:
                    detailData['artwork_materials'] = dpart
                if yps:
                    detailData['artwork_start_year'] = yps.groups()[0]
                if sps:
                    detailData['artwork_markings'] = sps.groups()[0]
                if pps and descparts.__len__() > dctr + 1:
                    detailData['artwork_provenance'] = descparts[dctr + 1]
                    detailData['artwork_provenance'] = detailData['artwork_provenance'].replace("\n", "").replace("\r", "")
                    detailData['artwork_provenance'] = self.__class__.htmltagPattern.sub("", detailData['artwork_provenance'])
                if lps and descparts.__len__() > dctr + 1:
                    detailData['artwork_literature'] = descparts[dctr + 1]
                    detailData['artwork_literature'] = detailData['artwork_literature'].replace("\n", "").replace("\r", "")
                    detailData['artwork_literature'] = self.__class__.htmltagPattern.sub("", detailData['artwork_literature'])
                dctr += 1
            detailData['artwork_name'] = descparts[0]
            artwork_name = detailData['artwork_name']
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
        if 'artwork_size_notes' in detailData.keys():
            sizeparts = detailData['artwork_size_notes'].split("x")
            if sizeparts.__len__() > 0:
                detailData['artwork_measurements_height'] = sizeparts[0]
            if sizeparts.__len__() > 1:
                detailData['artwork_measurements_width'] = sizeparts[1]
                mups = re.search(measureunitPattern, detailData['artwork_measurements_width'])
                if mups:
                    detailData['auction_measureunit'] = mups.groups()[0]
                    detailData['artwork_measurements_width'] = measureunitPattern.sub("", detailData['artwork_measurements_width'])
            if sizeparts.__len__() > 2:
                detailData['artwork_measurements_depth'] = sizeparts[2]
                mups = re.search(measureunitPattern, detailData['artwork_measurements_depth'])
                if mups:
                    detailData['auction_measureunit'] = mups.groups()[0]
                    detailData['artwork_measurements_depth'] = measureunitPattern.sub("", detailData['artwork_measurements_depth'])
        imgtags = soup.find_all("img", {'class' : 'orientation'})
        if imgtags.__len__() > 0:
            imgurl = imgtags[0]['src']
            if not imgurl.startswith('https://'):
                imgurl = baseUrl + imgurl
            imagename1 = self.getImagenameFromUrl(imgurl)
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
            newname1 = auction_number + "__" + processedArtistName + "__" + lot_number + "_a"
            encryptedFilename = newname1
            imagepathparts = imgurl.split("/")
            defimageurl = "/".join(imagepathparts[:-2])
            encryptedFilename = str(encryptedFilename).replace("b'", "")
            encryptedFilename = str(encryptedFilename).replace("'", "")
            detailData['image1_name'] = str(encryptedFilename) + ".jpg"
            detailData['artwork_images1'] = imgurl
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


    def getInfoFromLotsData(self, htmldivtags, imagepath, downloadimages):
        baseUrl = "https://www.millon.com"
        info = []
        endSpacePattern = re.compile("\s+$", re.DOTALL)
        soldpricePattern = re.compile("([\d\s\.,]+)\s+€")
        beginspacePattern = re.compile("^\s+")
        artistnamePattern1 = re.compile("([^\(]+)\s+\((\d{4})\-(\d{4})\)\s*\(?(.*)\)?$", re.DOTALL)
        artistnamePattern2 = re.compile("([^\(]+)\s+$", re.DOTALL)
        signaturePattern = re.compile("(Handtekeningdragend)|(Getekend)|(Signatuur)", re.IGNORECASE)
        estimatePattern1 = re.compile("Schatting\:\s*\&([lg]{1})t;\s*€\s*(\d+)", re.IGNORECASE|re.DOTALL)
        estimatePattern2 = re.compile("Schatting\:\s*€\s*(\d+)\s*\-\s*(\d+)", re.IGNORECASE|re.DOTALL)
        soldpricePattern = re.compile("Hamerprijs\:\s*€\s*(\d+)")
        bdPattern1 = re.compile("\((\d{4})\-(\d{4})\)")
        bdPattern2 = re.compile("\(b[\.orn]{1,3}\s+(\d{4})\)")
        yearPattern = re.compile("(\d{4})")
        endcommaPattern = re.compile(",\s*$")
        matcatdict_en = {}
        matcatdict_fr = {}
        dutchtoenglishtransliteration = {'doek' : 'canvas', 'paneel' : 'panel', 'verdoekt' : 'shroud', 'mahonie' : 'mahogony', 'landschap' : 'landscape', 'metaal' : 'metal', 'board' : 'board', 'terracotta' : 'terracotta', 'brons' : 'bronze', 'acryl' : 'acrylic'}
        with open("docs/fineart_materials.csv", newline='') as mapfile:
        #with open("/root/artwork/deploydirnew/docs/fineart_materials.csv", newline='') as mapfile:
            mapreader = csv.reader(mapfile, delimiter=",", quotechar='"')
            for maprow in mapreader:
                matcatdict_en[maprow[1]] = maprow[3]
                matcatdict_fr[maprow[2]] = maprow[3]
        mapfile.close()
        for htmldiv in htmldivtags:
            data = {}
            data['lot_num'], data['artist_name'], data['artist_birth'], data['artist_death'], data['artwork_name'], data['artwork_measurements_height'], data['artwork_measurements_width'], data['artwork_measurements_depth'], data['artwork_materials'], data['price_estimate_min'], data['price_estimate_max'], data['price_sold'], data['artwork_markings'] = "", "", "", "", "", "", "", "", "", "", "", "", ""
            data['auction_num'] = self.saleno
            data['auction_location'] = self.auctionlocation
            data['auction_name'] = self.auctiontitle
            self.auctiondate = endSpacePattern.sub("", self.auctiondate)
            self.auctiondate = beginspacePattern.sub("", self.auctiondate)
            data['auction_start_date'] = self.auctiondate
            data['auction_house_name'] = "Millon"
            lotno = ""
            detailUrl = ""
            htmlContent = htmldiv.renderContents().decode('utf-8')
            s = BeautifulSoup(htmlContent, features="html.parser")
            lotnospan = s.find("span", {'class' : 'category'})
            if lotnospan is not None:
                lotno = lotnospan.renderContents().decode('utf-8')
                lotno = lotno.replace("\n", "").replace("\r", "")
                lotno = endSpacePattern.sub("", lotno)
                lotno = lotno.replace("Lot ", "")
                data['lot_num'] = lotno
            else:
                continue
            artisth3tag = s.find("h3")
            detailUrl = ""
            if artisth3tag is not None:
                artistcontents = artisth3tag.renderContents().decode('utf-8')
                artistcontents = artistcontents.replace("\n", "").replace("\r", "")
                artistcontents = self.__class__.htmltagPattern.sub("", artistcontents)
                artistname = beginspacePattern.sub("", artistcontents)
                bdps1 = re.search(bdPattern1, artistname)
                bdps2 = re.search(bdPattern2, artistname)
                if bdps1:
                    data['artist_birth'] = bdps1.groups()[0]
                    data['artist_death'] = bdps1.groups()[1]
                    artistname = bdPattern1.sub("", artistname)
                elif bdps2:
                    data['artist_birth'] = bdps2.groups()[0]
                    data['artist_death'] = ""
                    artistname = bdPattern2.sub("", artistname)
                data['artist_name'] = artistname
            if artisth3tag is not None:
                titletag = artisth3tag.findNext("p", {'class' : 'mt-1'})
            else:
                titletag = None
            if titletag is not None:
                titlecontents = titletag.renderContents().decode('utf-8')
                titlecontents = titlecontents.replace("\n", "").replace("\r", "")
                titlecontents = self.__class__.htmltagPattern.sub("", titlecontents)
                titlecontents = beginspacePattern.sub("", titlecontents)
                titlecontents = endSpacePattern.sub("", titlecontents)
                yps = re.search(yearPattern, titlecontents)
                if yps:
                    data['artwork_start_year'] = yps.groups()[0]
                    titlecontents = yearPattern.sub("", titlecontents)
                titlecontents = endcommaPattern.sub("", titlecontents)
                data['artwork_name'] = titlecontents
            anchortag = s.find("a")
            if anchortag is not None:
                detailUrl = baseUrl + anchortag['href']
            else:
                continue
            data['lot_origin_url'] = detailUrl
            pricespantag = s.find("span", {'class' : 'push warning bold'})
            if pricespantag is not None:
                soldprice = pricespantag.renderContents().decode('utf-8')
                soldprice = soldprice.replace("\n", "").replace("\r", "")
                soldprice = soldprice.replace("€", "")
                soldprice = beginspacePattern.sub("", soldprice)
                soldprice = endSpacePattern.sub("", soldprice)
                data['price_sold'] = soldprice
            #print(data['lot_num'] + " ## " + data['artist_name'] + " ## " + data['price_estimate_min'] + " ## " + data['price_estimate_max'] + " ## " + data['price_sold'] + " ## " + data['artwork_name'] + " ## " + data['artwork_markings'])
            print("Getting '%s'..."%data['lot_origin_url'])
            if detailUrl != "":
                detailsPageContent = self.getDetailsPage(detailUrl)
            else:
                detailsPageContent = ""
            if detailsPageContent == "":
                continue
            detailData = self.parseDetailPage(detailsPageContent, data['artist_name'], data['artwork_name'], self.saleno, lotno, imagepath, downloadimages)
            for k in detailData.keys():
                if k == 'artwork_name' and k in data.keys() and data[k] != "":
                    continue
                else:
                    data[k] = detailData[k]
            if 'price_sold' not in data.keys() or data['price_sold'] == "":
                data['price_sold'] = ""
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
            if 'artwork_materials' in data.keys():
                beginspacePattern = re.compile("^\s+")
                endspacePattern = re.compile("\s+$")
                materials = data['artwork_materials']
                materialparts = materials.split(" ")
                catfound = 0
                for matpart in materialparts:
                    #print(matpart)
                    if matpart in ['in', 'on', 'of', 'the', 'from']:
                        continue
                    try:
                        matPattern = re.compile(matpart, re.IGNORECASE|re.DOTALL)
                        for enkey in matcatdict_en.keys():
                            if re.search(matPattern, enkey):
                                data['artwork_category'] = matcatdict_en[enkey]
                                if data['artwork_category'] == "material_category":
                                    data['artwork_category'] = "Unknown"
                                catfound = 1
                                break
                        for frkey in matcatdict_fr.keys():
                            if re.search(matPattern, frkey):
                                data['artwork_category'] = matcatdict_fr[frkey]
                                if data['artwork_category'] == "material_category":
                                    data['artwork_category'] = "Unknown"
                                catfound = 1
                                break
                        if catfound:
                            break
                    except:
                        pass
            info.append(data)
        return info


    def getNextPage(self, requestUrl):
        request = urllib.request.Request(requestUrl, headers=self.httpHeaders)
        pageResponse = None
        try:
            pageResponse = self.opener.open(request)
            pagecontent = self.__class__._decodeGzippedContent(pageResponse.read())
        except:
            print ("Error: %s"%sys.exc_info()[1].__str__())
            pagecontent = ""
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
    pageurl = "http://216.137.189.57:8080/scrapers/finish/?scrapername=Millon&auctionnumber=%s&auctionurl=%s&scrapertype=2"%(auctionno, urllib.parse.quote(auctionurl))
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
    resultatPattern = re.compile("\/resultat\/?$")
    if not re.search(resultatPattern, auctionurl):
        auctionurl = auctionurl.strip("/")
        auctionurl = auctionurl + "/resultat"
    millon = MillonBot(auctionurl, auctionnumber)
    fp = open(csvpath, "w")
    fieldnames = ['auction_house_name', 'auction_location', 'auction_num', 'auction_start_date', 'auction_end_date', 'auction_name', 'lot_num', 'sublot_num', 'price_kind', 'price_estimate_min', 'price_estimate_max', 'price_sold', 'artist_name', 'artist_birth', 'artist_death', 'artist_nationality', 'artwork_name', 'artwork_year_identifier', 'artwork_start_year', 'artwork_end_year', 'artwork_materials', 'artwork_category', 'artwork_markings', 'artwork_edition', 'artwork_description', 'artwork_measurements_height', 'artwork_measurements_width', 'artwork_measurements_depth', 'artwork_size_notes', 'auction_measureunit', 'artwork_condition_in', 'artwork_provenance', 'artwork_exhibited', 'artwork_literature', 'artwork_images1', 'artwork_images2', 'artwork_images3', 'artwork_images4', 'artwork_images5', 'image1_name', 'image2_name', 'image3_name', 'image4_name', 'image5_name', 'lot_origin_url']
    fieldsstr = ",".join(fieldnames)
    fp.write(fieldsstr + "\n")
    page = 1
    lastlotstartnum = 0
    while True:
        soup = BeautifulSoup(millon.currentPageContent, features="html.parser")
        lotsdata = millon.getLotsFromPage()
        if lotsdata.__len__() == 0:
            break
        info = millon.getInfoFromLotsData(lotsdata, imagepath, downloadimages)
        if info.__len__() > 0:
            lotstartnum = info[0]['lot_num']
            if int(lotstartnum) == int(lastlotstartnum):
                break
            lastlotstartnum = lotstartnum
        for d in info:
            for f in fieldnames:
                if f in d and d[f] is not None:
                    fp.write('"' + str(d[f]) + '",')
                else:
                    fp.write('"",')
            fp.write("\n")
        page = page + 1
        nextpageurl = auctionurl + "/page%s"%page
        print(nextpageurl)
        millon.currentPageContent = millon.getNextPage(nextpageurl)
    fp.close()
    updatestatus(auctionnumber, auctionurl)

# Example: python millon.py "https://www.millon.com/catalogue/vente1781-affiches-de-collections/resultat" 1781 /home/supmit/work/art2/millon_1781.csv /home/supmit/work/art2/images/millon/1781 0 0
# https://www.millon.com/catalogue/vente1781-affiches-de-collections/resultat


# supmit

