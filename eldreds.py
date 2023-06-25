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


class EldredsBot(object):
    
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
        soup = BeautifulSoup(pageContent, features="html.parser")
        timingdivtags = soup.find_all("div", {'class' : 'date-and-calendar'})
        if timingdivtags.__len__() > 0:
            timingcontents = timingdivtags[0].renderContents().decode('utf-8')
            timingcontents = self.__class__.htmltagPattern.sub("", timingcontents)
            datePattern = re.compile("([a-zA-Z]+\s+\d{1,2},\s+\d{4})")
            dps = re.search(datePattern, timingcontents)
            if dps:
                self.auctiondate = dps.groups()[0]
        alltitletags = soup.find_all("h1")
        if alltitletags.__len__() > 0:
            title = alltitletags[0].renderContents().decode('utf-8')
            title = title.replace("\n", "").replace("\r", "")
            self.auctiontitle = title
            trailingspacePattern = re.compile("\s+$")
            self.auctiontitle = trailingspacePattern.sub("", self.auctiontitle)
        lotblocks = soup.find_all("div", {'class' : 'lot-title-block'})
        if lotblocks.__len__() > 0:
            return lotblocks
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
        baseUrl = "https://www.eldreds.com"
        detailData = {}
        soup = BeautifulSoup(detailsPage, features="html.parser")
        mediumPattern = re.compile("(gold)|(silver)|(brass)|(bronze)|(wood)|(porcelain)|(stone)|(marble)|(metal)|(steel)|(iron)|(glass)|(plexiglas)|(chromogenic)|(paper)|(canvas)|(masonite)|(newsprint)|(silkscreen)|(parchment)|(linen)|(inkjet)|(ink\s+jet)|(pigment)|(\stin\s)|(photogravure)|(^oil\s+)|(\s+panel\s+)|(terracotta)|(ivory)|(\s+oak\s+)|(^oak\s+)|(\s+oak$)|(alabaster)|(\s+ink\s+)|(pencil)|(albumen)|(oil\s+)|(\s+oil)|(panel)", re.DOTALL|re.IGNORECASE)
        nonenglishmediumPattern = re.compile("(crayon)|(encre)|(plume)|(plume\s+et\s+encre)|(papier)|(pastel)|(craie)|(gouachée)|(aquarelle)|(lithographique)|(plomb)|(huile)|(cuivre)|(toile)|(bronze)|(Plâtre)|(en\s+terre\s+de\s+faïence)", re.IGNORECASE|re.DOTALL)
        signedPattern = re.compile("signed\s+", re.IGNORECASE)
        editionPattern = re.compile("edition", re.IGNORECASE)
        conditionPattern = re.compile("condition", re.IGNORECASE)
        yearPattern = re.compile("(\d{4})\s*\-?\s*(\d{0,4})", re.DOTALL)
        measureunitPattern = re.compile("([a-zA-Z]{2})")
        multispacePattern = re.compile("\s+")
        beginspacePattern = re.compile("^\s+")
        realizedpricePattern = re.compile("lotRealizedPrice")
        matcatdict_en = {}
        matcatdict_fr = {}
        with open("docs/fineart_materials.csv", newline='') as mapfile:
        #with open("/root/artwork/deploydirnew/docs/fineart_materials.csv", newline='') as mapfile:
            mapreader = csv.reader(mapfile, delimiter=",", quotechar='"')
            for maprow in mapreader:
                matcatdict_en[maprow[1]] = maprow[3]
                matcatdict_fr[maprow[2]] = maprow[3]
        mapfile.close()
        lotdetaildivtag = soup.find("div", {'id' : 'lotDescriptionFields'})
        detailfields = lotdetaildivtag.find_all("div")
        for detaildatatag in detailfields:
            detaildata = detaildatatag.renderContents().decode('utf-8')
            detaildata = detaildata.replace("\n", "").replace("\r", "")
            sps = re.search(signedPattern, detaildata)
            if sps:
                detailData['artwork_markings'] = detaildata
                detailData['artwork_markings'] = detailData['artwork_markings'].replace('"', "'").replace(";", " ")
            cps = re.search(conditionPattern, detaildata)
            if cps:
                detailData['artwork_condition_in'] = detaildata
                detailData['artwork_condition_in'] = detailData['artwork_condition_in'].replace("Condition: ", "")
                detailData['artwork_condition_in'] = self.__class__.htmltagPattern.sub("", detailData['artwork_condition_in'])
                detailData['artwork_condition_in'] = detailData['artwork_condition_in'].replace('"', "'").replace(";", " ")
        pricedivtag = soup.find("div", {'class' : realizedpricePattern})
        pricecontents = pricedivtag.renderContents().decode('utf-8')
        pricecontents = self.__class__.htmltagPattern.sub("", pricecontents)
        pricecontents = pricecontents.replace("\n", "").replace("\r", "")
        pricePattern = re.compile("Hammer\s+Price\:\s*\$([\d\,\.]+)", re.IGNORECASE)
        pps = re.search(pricePattern, pricecontents)
        if pps:
            detailData['price_sold'] = pps.groups()[0]
        estimatedivtag = soup.find("div", {'class' : 'lotEstimatedPrice'})
        estimatecontents = estimatedivtag.renderContents().decode('utf-8')
        estimatecontents = self.__class__.htmltagPattern.sub("", estimatecontents)
        estimatecontents = estimatecontents.replace("\n", "").replace("\r", "")
        estimatePattern = re.compile("Estimate\:\s*\$([\d\,\.]+)\s*-\s*\$([\d\,\.]+)", re.IGNORECASE)
        eps = re.search(estimatePattern, estimatecontents)
        if eps:
            detailData['price_estimate_min'] = eps.groups()[0]
            detailData['price_estimate_max'] = eps.groups()[1]
        desccontents = lotdetaildivtag.renderContents().decode('utf-8')
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
        detailData['artwork_description'] = detailData['artwork_description'].replace('"', "")
        detailData['artwork_description'] = detailData['artwork_description'].replace(';', " ")
        imgbtntag = soup.find("div", {'id' : 'reactField'})
        defaultimageurl = ""
        if imgbtntag:
            defaultimageurl = imgbtntag['href']
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
        detailData['auction_house_name'] = "Eldreds"
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
        baseUrl = "https://www.eldreds.com"
        info = []
        endSpacePattern = re.compile("\s+$", re.DOTALL)
        beginspacePattern = re.compile("^\s+")
        emptyspacePattern = re.compile("^\s*$")
        trailingdotPattern = re.compile("\.\s*$")
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
            data['artist_birth'] = ""
            htmlContent = htmldiv.renderContents().decode('utf-8')
            s = BeautifulSoup(htmlContent, features="html.parser")
            anchortags = s.find_all("a")
            if anchortags.__len__() > 0:
                anchortag = anchortags[0]
                detailUrl = self.baseUrl + anchortag['href']
                data['lot_origin_url'] = detailUrl
            htmlContent = htmlContent.replace("\n", "").replace("\r", "")
            htmlContent = self.__class__.htmltagPattern.sub("", htmlContent)
            htmlContent = htmlContent.replace("”", '"').replace("“", '"')
            titlePattern1 = re.compile("(\d+)\:\s+([^\(]+)\s+\(([\s\w\/]+),\s+(\d{4})\-(\d{4})\)\,\s+([^\,]+)\,\s+([^\,]+)\,\s+([\d\"\.]+\s+x\s+[\d\"\.]+)\s+")
            titlePattern2 = re.compile("(\d+)\:\s+([^\(]+)\s+\(([\s\w]+),\s+(\d{4})\-(\d{4})\)\,\s+([\w\s]+)")
            titlePattern3 = re.compile("(\d+)\:\s+([^\(]+)\s+\(([^\)]+)\)\,\s+([^\,]+)\,\s+([^\,]+)\,\s+([\d\"\.]+\s+x\s+[\d\"\.]+)\s+")
            titlePattern4 = re.compile("(\d+)\:\s+([a-zA-Z\s\(\)]+)\s+\(([\s\w\/]+),\s+(\d{4})-(\d{4})\)\,\s+([^\,]+)\,\s+([^\,]+)\,\s+([\d\"\.]+\s+x\s+[\d\"\.]+)\s+")
            titlePattern5 = re.compile("(\d+)\:\s+([^\(]+)\s+\(([\s\w\/]+),\s+(\d{4})\-(\d{4})\)\,\s+\"([^\"]+)\"\.?\,\s+([^\,]+)\,\s+([\d\"\.]+\s+x\s+[\d\"\.]+)\s+")
            titlePattern6 = re.compile("(\d+)\:\s+([^\(]+)\s+\(([\s\w\/]+),\s+(\d{4})\-(\d{4})\)\,\s+([^\.]+)\.?\,\s+([^\,]+)\,\s+([\d\"\.]+\s+x\s+[\d\"\.]+)\s+")
            titlePattern7 = re.compile("([\da-zA-Z]+)\:\s+([^\(]+)\s+\(([\s\w\/]+),\s+b\.\s+(\d{4})\)\,\s+([^\.]+)\.?\,\s+([^\,]+)\,\s+([\d\"\.]+\s+x\s+[\d\"\.]+)\s+")
            titlePattern8 = re.compile("([\da-zA-Z]+)\:\s+([^\(]+)\s+\(([\s\w\/]+),\s+(\d{4})\-(\d{4})\)\,\s+([^\.]+)\.?\,\s+([^\,]+)\,\s+([\d\"\.]+\s+x\s+[\d\"\.]+)\s+")
            titlePattern9 = re.compile("(\d+)\:\s+([^\(]+)\s+\(([\s\w\/\,]+)\)\,\s+([^\.]+)\.\,\s+([^\,]+)\,\s+([\d\"\.]+\s+x\s+[\d\"\.]+)\s+") # 11: CONTINENTAL SCHOOL (19th Century,), View of a distant town, likely the Mediterranean., Oil on panel, 8.5" x 3.5". Framed 12" x 7".
            titlePattern10 = re.compile("(\d+)\:\s+([^\(]+)\s+\(([\s\w\/]+),\s+(\d{4})\-(\d{4})\)\,\s+([^\,]+)\,\s+([^\,]+)\,[\s\w]+([\d\"\.]+\s+x\s+[\d\"\.]+)")
            titlePattern11 = re.compile("(\d+)\:\s+([A-Z\s]+)\s+([\w\s\d]+[Cc]entury)\s+[a-zA-Z\s]*[hH]eight\s+([\d\.]+\")\.[a-zA-Z\s\d\"\.]*[Ww]idth\s+([\d\.]+\")") # 569: CONTINENTAL CARVED AND UPHOLSTERED ARMCHAIR Early 20th Century Back height 39". Seat height 18". Width 26.5".
            titlePattern12 = re.compile("(\d+)\:\s+([A-Z\s]+)\s+([\w\s\d]+[Cc]entury)\s+[a-zA-Z\s]*[hH]eights?\s+([\d\.]+\")")
            titlePattern13 = re.compile("(\d+)\:\s+([A-Z\s]+)\s+([\w\s\d]+[Cc]entury)\s+[a-zA-Z\s]*[hH]eights?\s+[a-zA-Z]+\s+([\d\.]+\")")
            titlePattern14 = re.compile("(\d+)\:\s+[\w\s]*\"([A-Z\s\:,\.]+)\"\s+[a-zA-Z\s]*([\d\.\"]+\s*x\s*[\d\.\"]+)")
            tps1 = re.search(titlePattern1, htmlContent)
            tps2 = re.search(titlePattern2, htmlContent)
            tps3 = re.search(titlePattern3, htmlContent)
            tps4 = re.search(titlePattern4, htmlContent)
            tps5 = re.search(titlePattern5, htmlContent)
            tps6 = re.search(titlePattern6, htmlContent)
            tps7 = re.search(titlePattern7, htmlContent)
            tps8 = re.search(titlePattern8, htmlContent)
            tps9 = re.search(titlePattern9, htmlContent)
            tps10 = re.search(titlePattern10, htmlContent)
            tps11 = re.search(titlePattern11, htmlContent)
            tps12 = re.search(titlePattern12, htmlContent)
            tps13 = re.search(titlePattern13, htmlContent)
            tps14 = re.search(titlePattern14, htmlContent)
            if tps1:
                data['lot_num'] = tps1.groups()[0]
                lotno = data['lot_num']
                data['artist_name'] = tps1.groups()[1]
                data['artist_nationality'] = tps1.groups()[2]
                data['artist_birth'] = tps1.groups()[3]
                data['artist_death'] = tps1.groups()[4]
                data['artwork_name'] = tps1.groups()[5]
                data['artwork_name'] = data['artwork_name'].replace('"', "").replace("'", "")
                data['artwork_materials'] = tps1.groups()[6]
                data['artwork_size_notes'] = tps1.groups()[7]
                data['artwork_size_notes'] = data['artwork_size_notes'].replace('"', "in")
                #print(data['artwork_size_notes'])
            elif tps2:
                data['lot_num'] = tps2.groups()[0]
                lotno = data['lot_num']
                data['artist_name'] = tps2.groups()[1]
                data['artist_nationality'] = tps2.groups()[2]
                data['artist_birth'] = tps2.groups()[3]
                data['artist_death'] = tps2.groups()[4]
                data['artwork_name'] = tps2.groups()[5]
                data['artwork_name'] = data['artwork_name'].replace('"', "").replace("'", "")
            elif tps3:
                data['lot_num'] = tps3.groups()[0]
                lotno = data['lot_num']
                data['artist_name'] = tps3.groups()[1]
                data['artist_birth'] = tps3.groups()[2]
                data['artwork_name'] = tps3.groups()[3]
                data['artwork_name'] = data['artwork_name'].replace('"', "").replace("'", "")
                data['artwork_materials'] = tps3.groups()[4]
                data['artwork_size_notes'] = tps3.groups()[5]
                data['artwork_size_notes'] = data['artwork_size_notes'].replace('"', "in")
                #print(data['artwork_size_notes'])
            elif tps4:
                data['lot_num'] = tps4.groups()[0]
                lotno = data['lot_num']
                data['artist_name'] = tps4.groups()[1]
                data['artist_nationality'] = tps4.groups()[2]
                data['artist_birth'] = tps4.groups()[3]
                data['artist_death'] = tps4.groups()[4]
                data['artwork_name'] = tps4.groups()[5]
                data['artwork_name'] = data['artwork_name'].replace('"', "").replace("'", "")
                data['artwork_materials'] = tps4.groups()[6]
                data['artwork_size_notes'] = tps4.groups()[7]
                data['artwork_size_notes'] = data['artwork_size_notes'].replace('"', "in")
            elif tps5:
                data['lot_num'] = tps5.groups()[0]
                lotno = data['lot_num']
                data['artist_name'] = tps5.groups()[1]
                data['artist_nationality'] = tps5.groups()[2]
                data['artist_birth'] = tps5.groups()[3]
                data['artist_death'] = tps5.groups()[4]
                data['artwork_name'] = tps5.groups()[5]
                data['artwork_name'] = data['artwork_name'].replace('"', "").replace("'", "")
                data['artwork_materials'] = tps5.groups()[6]
                data['artwork_size_notes'] = tps5.groups()[7]
                data['artwork_size_notes'] = data['artwork_size_notes'].replace('"', "in")
                #print(data['artwork_size_notes'])
            elif tps6:
                data['lot_num'] = tps6.groups()[0]
                lotno = data['lot_num']
                data['artist_name'] = tps6.groups()[1]
                data['artist_nationality'] = tps6.groups()[2]
                data['artist_birth'] = tps6.groups()[3]
                data['artist_death'] = tps6.groups()[4]
                data['artwork_name'] = tps6.groups()[5]
                data['artwork_name'] = data['artwork_name'].replace('"', "").replace("'", "")
                data['artwork_materials'] = tps6.groups()[6]
                data['artwork_size_notes'] = tps6.groups()[7]
                data['artwork_size_notes'] = data['artwork_size_notes'].replace('"', "in")
                #print(data['artwork_size_notes'])
            elif tps7:
                data['lot_num'] = tps7.groups()[0]
                lotno = data['lot_num']
                data['artist_name'] = tps7.groups()[1]
                data['artist_nationality'] = tps7.groups()[2]
                data['artist_birth'] = tps7.groups()[3]
                data['artwork_name'] = tps7.groups()[4]
                data['artwork_name'] = data['artwork_name'].replace('"', "").replace("'", "")
                data['artwork_materials'] = tps7.groups()[5]
                data['artwork_size_notes'] = tps7.groups()[6]
                data['artwork_size_notes'] = data['artwork_size_notes'].replace('"', "in")
                #print(data['artwork_size_notes'])
            elif tps8:
                data['lot_num'] = tps8.groups()[0]
                lotno = data['lot_num']
                data['artist_name'] = tps8.groups()[1]
                data['artist_nationality'] = tps8.groups()[2]
                data['artist_birth'] = tps8.groups()[3]
                data['artist_death'] = tps8.groups()[4]
                data['artwork_name'] = tps8.groups()[5]
                data['artwork_name'] = data['artwork_name'].replace('"', "").replace("'", "")
                data['artwork_materials'] = tps8.groups()[6]
                data['artwork_size_notes'] = tps8.groups()[7]
                data['artwork_size_notes'] = data['artwork_size_notes'].replace('"', "in")
                #print(data['artwork_size_notes'])
            elif tps9:
                data['lot_num'] = tps9.groups()[0]
                lotno = data['lot_num']
                data['artist_name'] = tps9.groups()[1]
                data['artist_birth'] = tps9.groups()[2]
                data['artwork_name'] = tps9.groups()[3]
                data['artwork_name'] = data['artwork_name'].replace('"', "").replace("'", "")
                data['artwork_materials'] = tps9.groups()[4]
                data['artwork_size_notes'] = tps9.groups()[5]
                data['artwork_size_notes'] = data['artwork_size_notes'].replace('"', "in")
                #print(data['artwork_size_notes'])
            elif tps10:
                data['lot_num'] = tps10.groups()[0]
                lotno = data['lot_num']
                data['artist_name'] = tps10.groups()[1]
                data['artist_nationality'] = tps10.groups()[2]
                data['artist_birth'] = tps10.groups()[3]
                data['artist_death'] = tps10.groups()[4]
                data['artwork_name'] = tps10.groups()[5]
                data['artwork_name'] = data['artwork_name'].replace('"', "").replace("'", "")
                data['artwork_materials'] = tps10.groups()[6]
                data['artwork_size_notes'] = tps10.groups()[7]
                data['artwork_size_notes'] = data['artwork_size_notes'].replace('"', "in")
                #print(data['artwork_size_notes'])
            elif tps11:
                data['lot_num'] = tps11.groups()[0]
                data['artist_name'] = ""
                data['artwork_name'] = tps11.groups()[1]
                data['artist_birth'] = tps11.groups()[2]
                height = tps11.groups()[3].replace('"', "in")
                width = tps11.groups()[4].replace('"', "in")
                data['artwork_size_notes'] = height + " x " + width
            elif tps12:
                data['lot_num'] = tps12.groups()[0]
                data['artist_name'] = ""
                data['artwork_name'] = tps12.groups()[1]
                data['artist_birth'] = tps12.groups()[2]
                height = tps12.groups()[3].replace('"', "in")
                data['artwork_size_notes'] = height
            elif tps13:
                data['lot_num'] = tps13.groups()[0]
                data['artist_name'] = ""
                data['artwork_name'] = tps13.groups()[1]
                data['artist_birth'] = tps13.groups()[2]
                height = tps13.groups()[3].replace('"', "in")
                data['artwork_size_notes'] = height
            elif tps14:
                data['lot_num'] = tps14.groups()[0]
                data['artist_name'] = ""
                data['artwork_name'] = tps14.groups()[1]
                data['artwork_size_notes'] = tps14.groups()[2].replace('"', "in")
            if 'artwork_size_notes' in data.keys():
                sizeparts = data['artwork_size_notes'].split("x")
                if 'in' in data['artwork_size_notes']:
                    data['auction_measureunit'] = "in"
                data['artwork_measurements_height'] = sizeparts[0]
                data['artwork_measurements_height'] = data['artwork_measurements_height'].replace("in", "")
                data['artwork_measurements_height'] = trailingdotPattern.sub("", data['artwork_measurements_height'])
                if sizeparts.__len__() > 1:
                    data['artwork_measurements_width'] = sizeparts[1]
                    data['artwork_measurements_width'] = data['artwork_measurements_width'].replace("in", "")
                    data['artwork_measurements_width'] = trailingdotPattern.sub("", data['artwork_measurements_width'])
                if sizeparts.__len__() > 2:
                    data['artwork_measurements_depth'] = sizeparts[2]
                    data['artwork_measurements_depth'] = data['artwork_measurements_depth'].replace("in", "")
                    data['artwork_measurements_depth'] = trailingdotPattern.sub("", data['artwork_measurements_depth'])
            #print(data['lot_num'] + " ## " + data['artist_name'] + " ## " + data['artwork_name'] + " ## " + data['artist_birth'])
            print("Getting '%s'..."%data['lot_origin_url'])
            if detailUrl == "":
                break
            detailsPageContent = self.getDetailsPage(detailUrl)
            detailData = self.parseDetailPage(detailsPageContent, lotno, imagepath, data['artist_name'], data['artwork_name'], downloadimages)
            for k in detailData.keys():
                data[k] = detailData[k]
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
            data['auction_location'] = "Connecticut"
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
    pageurl = "http://216.137.189.57:8080/scrapers/finish/?scrapername=Eldreds&auctionnumber=%s&auctionurl=%s&scrapertype=2"%(auctionno, urllib.parse.quote(auctionurl))
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
    eldreds = EldredsBot(auctionurl, auctionnumber)
    fp = open(csvpath, "w")
    fieldnames = ['auction_house_name', 'auction_location', 'auction_num', 'auction_start_date', 'auction_end_date', 'auction_name', 'lot_num', 'sublot_num', 'price_kind', 'price_estimate_min', 'price_estimate_max', 'price_sold', 'artist_name', 'artist_birth', 'artist_death', 'artist_nationality', 'artwork_name', 'artwork_year_identifier', 'artwork_start_year', 'artwork_end_year', 'artwork_materials', 'artwork_category', 'artwork_markings', 'artwork_edition', 'artwork_description', 'artwork_measurements_height', 'artwork_measurements_width', 'artwork_measurements_depth', 'artwork_size_notes', 'auction_measureunit', 'artwork_condition_in', 'artwork_provenance', 'artwork_exhibited', 'artwork_literature', 'artwork_images1', 'artwork_images2', 'artwork_images3', 'artwork_images4', 'artwork_images5', 'image1_name', 'image2_name', 'image3_name', 'image4_name', 'image5_name', 'lot_origin_url']
    fieldsstr = ",".join(fieldnames)
    fp.write(fieldsstr + "\n")
    pagectr = 1
    soup = BeautifulSoup(eldreds.currentPageContent, features="html.parser")
    while True:
        lotsdata = eldreds.getLotsFromPage()
        if lotsdata.__len__() == 0:
            break
        info = eldreds.getInfoFromLotsData(lotsdata, imagepath, downloadimages)
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
        nextpageUrl = auctionurl + "?pageNum=%s"%pagectr
        eldreds.pageRequest = urllib.request.Request(nextpageUrl, headers=eldreds.httpHeaders)
        try:
            eldreds.pageResponse = eldreds.opener.open(eldreds.pageRequest)
        except:
            print("Couldn't find the page %s"%str(pagectr))
            break
        eldreds.currentPageContent = eldreds.__class__._decodeGzippedContent(eldreds.getPageContent())
    fp.close()
    updatestatus(auctionnumber, auctionurl)

# Example: python eldreds.py "https://www.eldreds.com/auction-catalog/paintings-and-fine-art_R8504AE48E" R8504AE48E /home/supmit/work/art2/eldreds_R8504AE48E.csv /home/supmit/work/art2/images/eldreds/R8504AE48E 0 0
# supmit


