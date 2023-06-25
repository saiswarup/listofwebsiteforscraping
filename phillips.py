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
    entitiesDict = {'&nbsp;' : ' ', '&quot;' : '"', '&lt;' : '<', '&gt;' : '>', '&amp;' : '&', '&apos;' : "'", '&#160;' : ' ', '&#60;' : '<', '&#62;' : '>', '&#38;' : '&', '&#34;' : '"', '&#39;' : "'",}
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


class PhillipsBot(object):
    startUrl=r"https://www.phillips.com/auctions/auction/UK040121"
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
        self.httpHeaders = { 'User-Agent' : r'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36',  'Accept' : 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9', 'Accept-Language' : 'en-GB,en-US;q=0.9,en;q=0.8', 'Accept-Encoding' : 'gzip, deflate', 'Connection' : 'keep-alive', 'Host' : 'www.phillips.com'}
        self.httpHeaders['Cache-Control'] = "max-age=0"
        self.httpHeaders['Upgrade-Insecure-Requests'] = "1"
        self.httpHeaders['Sec-Fetch-Dest'] = "document"
        self.httpHeaders['Sec-Fetch-Mode'] = "navigate"
        self.httpHeaders['Sec-Fetch-Site'] = "same-origin"
        self.httpHeaders['Sec-Fetch-User'] = "?1"
        self.httpHeaders['Cookie'] = ""
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
        #self.currentPageContent = str(self.getPageContent())
        self.currentPageNumber = 1 # Page number of the page that is currently being read.
        self.data = {'auction_house_name': '', 'auction_location' : '', 'auction_num' : '', 'auction_start_date' : '', 'auction_end_date' : '', 'auction_name' : '', 'lot_num' : '', 'sublot_num' : '', 'price_kind' : '', 'price_estimate_min' : '', 'price_estimate_max' : '', 'price_sold' : '', 'artist_name' : '', 'artist_birth' : '', 'artist_death' : '', 'artist_nationality' : '', 'artwork_name' : '', 'artwork_year_identifier' : '', 'artwork_start_year' : '', 'artwork_end_year' : '', 'artwork_materials' : '', 'artwork_category' : '', 'artwork_markings' : '', 'artwork_edition' : '', 'artwork_description' : '', 'artwork_measurements_height' : '', 'artwork_measurements_width' : '', 'artwork_measurements_depth' : '', 'artwork_size_notes' : '', 'auction_measureunit' : '', 'artwork_condition_in' : '', 'artwork_provenance' : '', 'artwork_exhibited' : '', 'artwork_literature' : '', 'artwork_images1' : '', 'artwork_images2' : '', 'artwork_images3' : '', 'artwork_images4' : '', 'artwork_images5' : '', 'image1_name' : '', 'image2_name' : '', 'image3_name' : '', 'image4_name' : '', 'image5_name' : '', 'lot_origin_url' : ''}
        self.saleno = auctionnumber
        self.currency = "USD"
        self.auctiontitle = ""
        self.auctionDate = ""


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
        if datestrcomponents.__len__() > 1 and datestrcomponents[1] in mondict.keys():
            mm = mondict[datestrcomponents[1]]
        elif datestrcomponents.__len__() > 1:
            mm = mondict3[datestrcomponents[1]]
        else:
            return datestr
        if datestrcomponents.__len__() > 2:
            yyyy = datestrcomponents[2]
        else:
            yyyy = '2021'
        retdate = mm + "/" + dd + "/" + yyyy
        return retdate

    formatDate = classmethod(formatDate)


    def getLotsFromPage(self):
        baseUrl = "https://www.phillips.com"
        pageContent = self.currentPageContent
        lotsdata = []
        soup = BeautifulSoup(pageContent, features="html.parser")
        alltitleh1tags = soup.find_all("h1", {'class' : 'auction-page__hero__title'})
        if alltitleh1tags.__len__() > 0:
            self.auctiontitle = alltitleh1tags[0].renderContents().decode('utf-8')
        alllotsdiv = soup.find_all("div", {'class' : 'phillips-lot'})
        for lotdiv in alllotsdiv:
            lotcontent = lotdiv.renderContents().decode('utf-8')
            lotsdata.append(lotcontent)
        datetags = soup.find_all("span", {'class' : 'auction-page__hero__date'})
        if datetags.__len__() > 0:
            datestring = datetags[0].renderContents().decode('utf-8')
            #datePattern = re.compile("\w+\s+\w+\s+([\d\w\s]+)", re.DOTALL)
            #datePattern = re.compile("\w+\s+\w+\s+\d*\s*\-\s*([\d\w\s]+)", re.DOTALL)
            datePattern = re.compile("[\w\s]+\s+(\d+\s+\w+\s+\d{4})", re.DOTALL)
            dps = re.search(datePattern, datestring)
            if dps:
                self.auctionDate = dps.groups()[0]
        return lotsdata
        

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
        baseUrl = "https://www.phillips.com"
        detailData = {}
        beginSpacePattern = re.compile("^\s+", re.DOTALL)
        newlinesPattern = re.compile("\\r?\\n|\\r", re.DOTALL)
        brPattern = re.compile("<br\s*\/?>", re.IGNORECASE|re.DOTALL)
        soup = BeautifulSoup(detailsPage, features="html.parser")
        lotinfoptags = soup.find_all("p", {'class' : 'lot-page__lot__additional-info'})
        if lotinfoptags.__len__() == 0:
            lotinfoptags = soup.find_all("div", {'class' : 'lot-page__lot'})
            if lotinfoptags.__len__() == 0:
                return detailData
        lotinfotag = lotinfoptags[0]
        lotinfotext = lotinfotag.renderContents().decode('utf-8')
        lotinfotextparts = lotinfotext.split("<br/>")
        signedPattern = re.compile("\s+signed", re.DOTALL|re.IGNORECASE)
        signedPattern2 = re.compile("^signed", re.DOTALL|re.IGNORECASE)
        #sizePattern = re.compile("\(([\d\.]*\s*by\s*[\d\.]*\s*[by]*\s*[\d\.]*\s+cm)\)", re.DOTALL|re.IGNORECASE)
        sheetPattern = re.compile("sheet:\s+([\d\.\sx]+\s+cm)\s+", re.DOTALL|re.IGNORECASE)
        sizePattern = re.compile("framed?:\s+([\d\.\sx]+\s+cm)\s+", re.DOTALL|re.IGNORECASE)
        sizePattern2 = re.compile("image:\s+([\d\.\sx]+\s+cm)\s+\(", re.DOTALL|re.IGNORECASE)
        sizePattern3 = re.compile("([\d\.\sx]+\s+cm)\s+\(", re.DOTALL|re.IGNORECASE)
        sizePattern4 = re.compile("([\d\.\/\sx]+\s+in)\.?\s+", re.DOTALL|re.IGNORECASE)
        mediumPattern = re.compile("(gold)|(silver)|(brass)|(bronze)|(wood)|(porcelain)|(stone)|(marble)|(metal)|(steel)|(iron)|(glass)|(plexiglas)|(chromogenic)|(paper)|(canvas)|(masonite)|(newsprint)|(silkscreen)|(parchment)|(linen)|(inkjet)|(ink\s+jet)|(pigment)|(\stin\s)|(photogravure)|(^oil\s+)|(\s+panel\s+)|(terracotta)|(ivory)|(\s+oak\s+)|(^oak\s+)|(\s+oak$)|(alabaster)|(platinum)|(aluminium)|(polaroid)|(dye\s+)|(plastic)|(egg\s+)|(velcro\s+)", re.DOTALL|re.IGNORECASE)
        printedPattern = re.compile("\s+printed\s+\w+\.?$", re.IGNORECASE|re.DOTALL)
        mountedPattern = re.compile(",?\s+mounted\s+\w*\.?$", re.IGNORECASE|re.DOTALL)
        editionPattern = re.compile("[\w\s]+number\s+(\d+)\s+from the[^\.]+\.", re.DOTALL|re.IGNORECASE)
        provenancePattern = re.compile("provenance", re.DOTALL|re.IGNORECASE)
        literaturePattern = re.compile("literature", re.DOTALL|re.IGNORECASE)
        exhibitedPattern = re.compile("exhibited", re.DOTALL|re.IGNORECASE)
        yearPattern = re.compile("(\d{4})\s*[\/\-]?(\d{0,4})", re.DOTALL|re.IGNORECASE)
        matcatdict_en = {}
        matcatdict_fr = {}
        #with open("docs/fineart_materials.csv", newline='') as mapfile:
        with open("/root/artwork/deploydirnew/docs/fineart_materials.csv", newline='') as mapfile:
            mapreader = csv.reader(mapfile, delimiter=",", quotechar='"')
            for maprow in mapreader:
                matcatdict_en[maprow[1]] = maprow[3]
                matcatdict_fr[maprow[2]] = maprow[3]
        mapfile.close()
        artistinfop = soup.find_all("p", {'class' : 'artist-info'})
        if artistinfop.__len__() > 0:
            artistinfotag = artistinfop[0]
            artistinfocontent = artistinfotag.renderContents().decode('utf-8')
            artistinfocontent = artistinfocontent.replace("<!--", "").replace("-->", "")
            birthdeathyearPattern = re.compile("b?\w*\.?\s*(\d{4})\s*\-?\s*(\d{0,4})", re.DOTALL)
            bdps = re.search(birthdeathyearPattern, artistinfocontent)
            if bdps and 'artist_birth' not in detailData.keys():
                bdpsg = bdps.groups()
                detailData['artist_birth'] = bdpsg[0]
                detailData['artist_death'] = bdpsg[1]
        authenticityPattern = re.compile("([^\.]+authenticity[^\.]+)\.", re.DOTALL|re.IGNORECASE)
        inscribedPattern = re.compile("Inscribed", re.DOTALL)
        conceivedPattern = re.compile("conceived\s+in\s+(\d{4})\-?(\d{0,4})", re.DOTALL|re.IGNORECASE)
        conditionPattern = re.compile("condition\s+report", re.DOTALL|re.IGNORECASE)
        editionnumberPattern = re.compile("edition[ed]*\s+(\d+)/(\d+)", re.DOTALL|re.IGNORECASE)
        measureunitPattern = re.compile("([a-zA-Z]{2})")
        heightPattern = re.compile("Height.*\:", re.DOTALL|re.IGNORECASE)
        for lottext in lotinfotextparts:
            lottext = self.__class__.htmltagPattern.sub("", lottext)
            lottext = newlinesPattern.sub("", lottext)
            szp = re.search(sizePattern, lottext)
            if szp and 'artwork_size_notes' not in detailData.keys():
                detailData['artwork_size_notes'] = szp.groups()[0]
            szp2 = re.search(sizePattern2, lottext)
            if szp2 and 'artwork_size_notes' not in detailData.keys():
                detailData['artwork_size_notes'] = szp2.groups()[0]
            szp3 = re.search(sizePattern3, lottext)
            if szp3 and 'artwork_size_notes' not in detailData.keys():
                detailData['artwork_size_notes'] = szp3.groups()[0]
            szp4 = re.search(sizePattern4, lottext)
            if szp4 and 'artwork_size_notes' not in detailData.keys():
                detailData['artwork_size_notes'] = szp4.groups()[0]
            if 'artwork_size_notes' in detailData.keys():
                detailData['artwork_size_notes'] = beginSpacePattern.sub("", detailData['artwork_size_notes'])
                #print(detailData['artwork_size_notes'])
                mups = re.search(measureunitPattern, detailData['artwork_size_notes'])
                if mups:
                    detailData['auction_measureunit'] = mups.groups()[0]
                sizeparts = detailData['artwork_size_notes'].split("x")
                detailData['artwork_measurements_height'] = sizeparts[0]
                if sizeparts.__len__() > 1:
                    detailData['artwork_measurements_width'] = sizeparts[1]
                    detailData['artwork_measurements_width'] = measureunitPattern.sub("", detailData['artwork_measurements_width'])
                if sizeparts.__len__() > 2:
                    detailData['artwork_measurements_depth'] = sizeparts[2]
            """
            shzp = re.search(sheetPattern, lottext)
            if shzp and 'SHEETSIZE' not in detailData.keys():
                detailData['SHEETSIZE'] = shzp.groups()[0]
            if 'SHEETSIZE' in detailData.keys():
                detailData['SHEETSIZE'] = beginSpacePattern.sub("", detailData['SHEETSIZE'])
            """
            mps = re.search(mediumPattern, lottext)
            if mps and 'artwork_materials' not in detailData.keys():
                detailData['artwork_materials'] = lottext
                detailData['artwork_materials'] = printedPattern.sub("", detailData['artwork_materials'])
                detailData['artwork_materials'] = mountedPattern.sub("", detailData['artwork_materials'])
            sgnp = re.search(signedPattern, lottext)
            if sgnp and 'artwork_markings' not in detailData.keys():
                detailData['artwork_markings'] = lottext
            sgnp2 = re.search(signedPattern2, lottext)
            if sgnp2 and 'artwork_markings' not in detailData.keys():
                detailData['artwork_markings'] = lottext
            enps = re.search(editionnumberPattern, lottext)
            if enps and 'artwork_edition' not in detailData.keys():
                detailData['artwork_edition'] = enps.groups()[0]
                editionparts = lottext.split(".")
                detailData['artwork_edition'] = editionparts[0]
        detailstags = soup.find_all("ul", {'class' : 'lot-page__details__list lot-page__details__list--sticky'})
        if detailstags.__len__() == 0:
            detailstags = soup.find_all("ul", {'class' : 'lot-page__details__list'})
            if detailstags.__len__() == 0:
                return detailData
        detailstext = detailstags[0].renderContents().decode('utf-8')
        detailstext = detailstext.replace("\n", " ")
        detailstextparts = detailstext.split("</p>")
        for textinfo in detailstextparts:
            textinfo = self.__class__.htmltagPattern.sub("", textinfo)
            prps = re.search(provenancePattern, textinfo)
            if prps and 'artwork_provenance' not in detailData.keys():
                detailData['artwork_provenance'] = textinfo
                detailData['artwork_provenance'] = detailData['artwork_provenance'].replace("Provenance", "")
                detailData['artwork_provenance'] = detailData['artwork_provenance'].replace('"', "'")
                detailData['artwork_provenance'] = detailData['artwork_provenance'].replace("Condition ReportSign UporLog In", "")
            exps = re.search(exhibitedPattern, textinfo)
            if exps and 'artwork_exhibited' not in detailData.keys():
                detailData['artwork_exhibited'] = textinfo
                detailData['artwork_exhibited'] = detailData['artwork_exhibited'].replace("Exhibited", "")
                detailData['artwork_exhibited'] = detailData['artwork_exhibited'].replace(",", "|")
                detailData['artwork_exhibited'] = detailData['artwork_exhibited'].replace('"', "'")
            ltps = re.search(literaturePattern, textinfo)
            if ltps and 'artwork_literature' not in detailData.keys():
                detailData['artwork_literature'] = textinfo
                detailData['artwork_literature'] = detailData['artwork_literature'].replace("Literature", "")
                detailData['artwork_literature'] = detailData['artwork_literature'].replace(",", "|")
                detailData['artwork_literature'] = detailData['artwork_literature'].replace('"', "'")
        imgmetatags = soup.find_all("meta", {'property' : 'og:image'})
        #print(imgmetatags.__len__())
        if imgmetatags.__len__() > 0:
            defaultimageurl = imgmetatags[0]['content']
            imgPattern = re.compile("t_Website_LotDetailMainImage\/v\d{1,}\/")
            imgparts = re.split(imgPattern, defaultimageurl)
            if imgparts.__len__() > 1:
                defaultimageurl = imgparts[0] + imgparts[1]
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
        addlimgmetatags = soup.find_all("meta", {'name' : 'twitter:image'})
        if addlimgmetatags.__len__() > 0:
            additionalimages = []
            for addltag in addlimgmetatags:
                additionalimages.append(addltag['content'])
            imgctr = 2
            if additionalimages.__len__() > 0:
                altimage2 = additionalimages[0]
                altimage2parts = altimage2.split("/")
                altimageurl = "/".join(altimage2parts[:-2])
                detailData['image' + str(imgctr) + '_name'] = self.getImagenameFromUrl(altimage2)
                processedAuctionTitle = self.auctiontitle.replace(" ", "_")
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
            if additionalimages.__len__() > 1:
                altimage3 = additionalimages[1]
                altimage3parts = altimage3.split("/")
                altimageurl = "/".join(altimage3parts[:-2])
                detailData['image' + str(imgctr) + '_name'] = self.getImagenameFromUrl(altimage3)
                processedAuctionTitle = self.auctiontitle.replace(" ", "_")
                processedArtistName = artistname.replace(" ", "_")
                processedArtistName = unidecode.unidecode(processedArtistName)
                processedArtworkName = artworkname.replace(" ", "_")
                sublot_number = ""
                #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + self.saleno + "__" + lotno + "__" + sublot_number
                newname1 = self.saleno + "__" + processedArtistName + "__" + lotno + "_c"
                #encryptedFilename = self.encryptFilename(newname1)
                encryptedFilename = newname1
                detailData['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
                detailData['artwork_images' + str(imgctr)] = altimage3
                imgctr += 1
            if additionalimages.__len__() > 2:
                altimage4 = additionalimages[2]
                altimage4parts = altimage4.split("/")
                altimageurl = "/".join(altimage4parts[:-2])
                detailData['image' + str(imgctr) + '_name'] = self.getImagenameFromUrl(altimage4)
                processedAuctionTitle = self.auctiontitle.replace(" ", "_")
                processedArtistName = artistname.replace(" ", "_")
                processedArtistName = unidecode.unidecode(processedArtistName)
                processedArtworkName = artworkname.replace(" ", "_")
                sublot_number = ""
                #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + self.saleno + "__" + lotno + "__" + sublot_number
                newname1 = self.saleno + "__" + processedArtistName + "__" + lotno + "_d"
                #encryptedFilename = self.encryptFilename(newname1)
                encryptedFilename = newname1
                detailData['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
                detailData['artwork_images' + str(imgctr)] = altimage4
                imgctr += 1
            if additionalimages.__len__() > 3:
                altimage5 = additionalimages[3]
                altimage5parts = altimage5.split("/")
                altimageurl = "/".join(altimage5parts[:-2])
                detailData['image' + str(imgctr) + '_name'] = self.getImagenameFromUrl(altimage5)
                processedAuctionTitle = self.auctiontitle.replace(" ", "_")
                processedArtistName = artistname.replace(" ", "_")
                processedArtistName = unidecode.unidecode(processedArtistName)
                processedArtworkName = artworkname.replace(" ", "_")
                sublot_number = ""
                #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + self.saleno + "__" + lotno + "__" + sublot_number
                newname1 = self.saleno + "__" + processedArtistName + "__" + lotno + "_e"
                #encryptedFilename = self.encryptFilename(newname1)
                encryptedFilename = newname1
                detailData['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
                detailData['artwork_images' + str(imgctr)] = altimage5
        """
        titletag = soup.find_all("title")[0]
        titlecontent = titletag.renderContents().decode('utf-8')
        ttps = re.search(yearPattern, titlecontent)
        if ttps:
            detailData['artwork_start_year'] = ttps.groups()[0]
            detailData['artwork_end_year'] = ttps.groups()[1]
        """
        yearinfotags = soup.find_all("p", {'class' : "lot-page__lot__additional-info"})
        if yearinfotags.__len__() > 0:
            yearinfotag = yearinfotags[0]
            yearinfocontents = yearinfotag.renderContents().decode('utf-8')
            yearinfo = re.search(yearPattern, yearinfocontents)
            if yearinfo:
                detailData['artwork_start_year'] = yearinfo.groups()[0]
                #print(detailData['artwork_start_year'])
                detailData['YEARTO'] = yearinfo.groups()[1]
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
        descdivtags1 = soup.find_all("div", {'class' : 'lot-page__lot'})
        detailData['artwork_description'] = ""
        if descdivtags1.__len__() > 0:
            descdivcontents1 = descdivtags1[0].renderContents().decode('utf-8')
            descdivcontents1 = descdivcontents1.replace("\n", "").replace("\r", "")
            descdivcontents1 = self.__class__.htmltagPattern.sub("", descdivcontents1)
            detailData['artwork_description'] = descdivcontents1
        descdivtags2 = soup.find_all("div", {'class' : 'lot-page__details'})
        if descdivtags2.__len__() > 0:
            descdivcontents2 = descdivtags2[0].renderContents().decode('utf-8')
            descdivcontents2 = descdivcontents2.replace("\n", "").replace("\r", "")
            descdivcontents2 = self.__class__.htmltagPattern.sub("", descdivcontents2)
            detailData['artwork_description'] += " " + descdivcontents2
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


    def getImage(self, imageUrl, imagepath, downloadimages):
        imageUrlParts = imageUrl.split("/")
        imagefilename = imageUrlParts[-2] + "_" + imageUrlParts[-1]
        imagedir = imageUrlParts[-2]
        headers = {}
        for k in self.httpHeaders.keys():
            headers[k] = self.httpHeaders[k]
        headers['Accept'] = "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9"
        headers['sec-fetch-dest'] = "document"
        headers['sec-fetch-mode'] = "navigate"
        headers['sec-fetch-site'] = "none"
        headers['sec-fetch-user'] = "?1"
        headers['upgrade-insecure-requests'] = "1"
        headers['Accept-Encoding'] = "gzip,deflate,br"
        headers['Cache-Control'] = "max-age=0"
        headers['Host'] = "assets.phillips.com"
        imageUrlSections = imageUrl.split("?url=")
        imgUrl = imageUrl
        if imageUrlSections.__len__() > 1:
            imgUrl = imageUrlSections[1]
        imgUrl = imgUrl.replace("%3A", ":").replace("%2F", "/")
        if downloadimages == "1":
            pageRequest = urllib.request.Request(imgUrl, headers=headers)
            pageResponse = None
            try:
                pageResponse = self.opener.open(pageRequest)
            except:
                print ("Error1: %s"%sys.exc_info()[1].__str__())
            try:
                imageContent = pageResponse.read()
                ifp = open(imagepath + os.path.sep + imagefilename, "wb")
                ifp.write(imageContent)
                ifp.close()
            except:
                print("Error2: %s"%sys.exc_info()[1].__str__())
        return imagefilename


    def getInfoFromLotsData(self, datalist, imagepath, downloadimages):
        baseUrl = "https://www.phillips.com"
        beginspacePattern = re.compile("^\s+", re.DOTALL)
        info = []
        for lotdata in datalist:
            data = {}
            lsoup = BeautifulSoup(lotdata, features="html.parser")
            lotnostrongs = lsoup.find_all("strong", {'class' : 'phillips-lot__description__lot-number-wrapper__lot-number'})
            if lotnostrongs.__len__() == 0:
                continue
            lotnostrong = lotnostrongs[0]
            lotno = lotnostrong.renderContents().decode('utf-8')
            try:
                artistp = lsoup.find_all("p", {'class' : 'phillips-lot__description__artist'})[0]
                artist = artistp.renderContents().decode('utf-8')
            except:
                artist = ""
            try:
                titlep = lsoup.find_all("p", {'class' : 'phillips-lot__description__title'})[0]
                title = titlep.renderContents().decode('utf-8')
            except:
                title = ""
            title = self.__class__.htmltagPattern.sub("", title)
            try:
                lotdetaildiv = lsoup.find_all("div", {'class' : 'phillips-lot__image'})[0]
                lotdetailanchor = lotdetaildiv.findChildren("a")[0]
                detailUrl = lotdetailanchor['href']
            except:
                detailUrl = ""
            estimateps = lsoup.find_all("p", {'class' : 'phillips-lot__description__estimate'})
            if estimateps.__len__() > 0:
                estimatep = estimateps[0]
                estimate = estimatep.renderContents().decode('utf-8')
                estimate = self.__class__.htmltagPattern.sub("", estimate)
                estimate = estimate.replace('"', "").replace("&nbsp;", " ")
                estimate = beginspacePattern.sub("", estimate)
                estimateparts = estimate.split(" - ")
                data['price_estimate_min'] = estimateparts[0]
                data['price_estimate_min'] = data['price_estimate_min'].replace("Estimate", "")
                data['price_estimate_min'] = data['price_estimate_min'].replace("$", "")
                data['price_estimate_min'] = data['price_estimate_min'].replace("£", "")
                data['price_estimate_min'] = beginspacePattern.sub("", data['price_estimate_min'])
                if estimateparts.__len__() > 1:
                    data['price_estimate_max'] = estimateparts[1]
            soldforps = lsoup.find_all("p", {'class' : 'phillips-lot__sold'})
            soldfor = "0"
            if soldforps.__len__() > 0:
                soldfor = soldforps[0].renderContents().decode('utf-8')
                soldfor = self.__class__.htmltagPattern.sub("", soldfor)
                soldfor = soldfor.replace('"', "").replace("&nbsp;", " ")
            soldfor = beginspacePattern.sub("", soldfor)
            soldfor = soldfor.replace("Sold for ", "")
            soldfor = soldfor.replace("$", "")
            soldfor = soldfor.replace("£", "")
            data['price_sold'] = soldfor
            data['artist_name'] = artist
            data['artist_name'] = data['artist_name'].replace('"', "")
            data['lot_num'] = lotno
            data['artwork_name'] = title
            data['artwork_name'] = data['artwork_name'].replace('"', "")
            data['lot_origin_url'] = detailUrl
            data['auction_house_name'] = "PHILLIPS"
            data['auction_num'] = self.saleno
            #print("%s ## %s ## %s ## %s ## %s"%(data['lot_num'], data['artist_name'], data['artwork_name'], data['price_estimate_min'], data['price_sold']))
            print("Getting '%s'..."%detailUrl)
            detailsPageContent = self.getDetailsPage(detailUrl)
            detailData = self.parseDetailPage(detailsPageContent, lotno, imagepath, artist, title, downloadimages)
            for k in detailData.keys():
                detailData[k] = detailData[k].replace('"', "")
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
            if 'price_sold' not in data.keys() or data['price_sold'] == "":
                data['price_sold'] = "0"
            self.auctionDate = self.auctionDate.replace("Auction ", "")
            #print(self.auctionDate)
            data['auction_start_date'] = self.__class__.formatDate(self.auctionDate)
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
    pageurl = "http://216.137.189.57:8080/scrapers/finish/?scrapername=Phillips&auctionnumber=%s&auctionurl=%s&scrapertype=2"%(auctionno, urllib.parse.quote(auctionurl))
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
    phillips = PhillipsBot(auctionurl, auctionnumber)
    fp = open(csvpath, "w")
    fieldnames = ['auction_house_name', 'auction_location', 'auction_num', 'auction_start_date', 'auction_end_date', 'auction_name', 'lot_num', 'sublot_num', 'price_kind', 'price_estimate_min', 'price_estimate_max', 'price_sold', 'artist_name', 'artist_birth', 'artist_death', 'artist_nationality', 'artwork_name', 'artwork_year_identifier', 'artwork_start_year', 'artwork_end_year', 'artwork_materials', 'artwork_category', 'artwork_markings', 'artwork_edition', 'artwork_description', 'artwork_measurements_height', 'artwork_measurements_width', 'artwork_measurements_depth', 'artwork_size_notes', 'auction_measureunit', 'artwork_condition_in', 'artwork_provenance', 'artwork_exhibited', 'artwork_literature', 'artwork_images1', 'artwork_images2', 'artwork_images3', 'artwork_images4', 'artwork_images5', 'image1_name', 'image2_name', 'image3_name', 'image4_name', 'image5_name', 'lot_origin_url']
    fieldsstr = ",".join(fieldnames)
    fp.write(fieldsstr + "\n")
    lotsdata = phillips.getLotsFromPage()
    info = phillips.getInfoFromLotsData(lotsdata, imagepath, downloadimages)
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
    

# Example: python phillips.py https://www.phillips.com/auctions/auction/UK040121 UK040121 /home/supmit/work/artwork/phillips_UK040121.csv /home/supmit/work/artwork/images/phillips/UK040121 0 0
# supmit

