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
from cryptography.fernet import Fernet
from urllib.parse import urlencode, quote_plus
import html, csv
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


class GrisebachBot(object):
    
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
        return decoded_content

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
            return b""

    def formatDate(cls, datestr):
        mondict = {'January' : '01', 'February' : '02', 'March' : '03', 'April' : '04', 'May' : '05', 'June' : '06', 'July' : '07', 'August' : '08', 'September' : '09', 'October' : '10', 'November' : '11', 'December' : '12' }
        mondict3 = {'jan.' : '01', 'fév.' : '02', 'mar.' : '03', 'avr.' : '04', 'mai.' : '05', 'jui.' : '06', 'jul.' : '07', 'aoû.' : '08', 'sep.' : '09', 'oct.' : '10', 'nov.' : '11', 'déc.' : '12' }
        mondict4 = {'Janvier' : '01', 'Février' : '02', 'Mars' : '03', 'Avril' : '04', 'Mai' : '05', 'Juin' : '06', 'Juillet' : '07', 'Août' : '08', 'Septembre' : '09', 'Octobre' : '10', 'Novembre' : '11', 'Décembre' : '12'}
        datestrcomponents = datestr.split(" ")
        if not datestr:
            return ""
        if datestrcomponents.__len__() < 3:
            return ""
        dd = datestrcomponents[0]
        mon = datestrcomponents[1].capitalize()
        year = datestrcomponents[2][2:]
        monstr = mon[:3] # Taking first 3 characters
        #if mon in mondict.keys():
        #    monstr = mondict[mon]
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
        allselecttags = soup.find_all("select", {'name' : 'katalog[kat_id]'})
        if allselecttags.__len__() > 0:
            alloptions = allselecttags[0].find_all("option", {'selected' : True})
            if alloptions.__len__() > 0:
                self.auctiontitle = alloptions[0].renderContents().decode('utf-8')
        lotPattern = re.compile("lot_\d{6,7}")
        lotblocks = soup.find_all("div", {'id' : lotPattern})
        return lotblocks
        

    def getDetailsPage(self, detailUrl):
        self.requestUrl = detailUrl
        self.pageRequest = urllib.request.Request(self.requestUrl, headers=self.httpHeaders)
        self.pageResponse = None
        self.postData = {}
        print("Opening detail page...")
        try:
            self.pageResponse = self.opener.open(self.pageRequest)
            headers = self.pageResponse.getheaders()
        except:
            print ("Couldn't fetch page due to limited connectivity. Please check your internet connection and try again. %s"%sys.exc_info()[1].__str__())
        print("Detail page opened...")
        self.currentPageContent = self.__class__._decodeGzippedContent(self.getPageContent())
        print("Detail page read...")
        return self.currentPageContent


    def renameImageFile(self, basepath, imagefilename, mappedImagename):
        oldfilename = basepath + "/" + imagefilename
        newfilename = basepath + "/" + mappedImagename
        try:
            os.rename(oldfilename, newfilename)
        except:
            pass

    def encryptFilename(self, filename):
        k = Fernet.generate_key()
        f = Fernet(k)
        encfilename = f.encrypt(filename.encode())
        return encfilename


    def getImagenameFromUrl(self, imageUrl):
        urlparts = imageUrl.split("/")
        imagefilepart = urlparts[-1]
        imagefilenameparts = imagefilepart.split("?")
        imagefilename = imagefilenameparts[0]
        return imagefilename


    def parseDetailPage(self, detailsPage, lotno, imagepath, downloadimages, artworkname, artistname):
        baseUrl = "https://www.grisebach.com"
        detailData = {}
        soup = BeautifulSoup(detailsPage, features="html.parser")
        mediumPattern = re.compile("(gold\s+)|(silver)|(brass)|(bronze)|(wood)|(porcelain)|(stone)|(marble)|(metal)|(steel)|(iron)|(glass)|(plexiglas)|(chromogenic)|(paper)|(canvas)|(masonite)|(newsprint)|(silkscreen)|(parchment)|(linen)|(inkjet)|(ink\s+jet)|(pigment)|(\stin\s)|(photogravure)|(^oil\s+)|(\s+panel\s+)|(terracotta)|(ivory)|(\s+oak\s+)|(^oak\s+)|(\s+oak$)|(alabaster)|(c\-print)|(polaroid)|(travertine)|(\s+cardboard)|(alcohol)|(acrylic)|(concrete)", re.DOTALL|re.IGNORECASE)
        nonenglishmediumPattern = re.compile("(crayon)|(encre)|(plume)|(plume\s+et\s+encre)|(papier)|(pastel)|(craie)|(gouachée)|(aquarelle)|(lithographique)|(plomb)|(huile)|(cuivre)|(toile)|(bronze)|(Plâtre)|(en\s+terre\s+de\s+faïence)", re.IGNORECASE|re.DOTALL)
        signedPattern = re.compile("signed", re.IGNORECASE)
        editionPattern = re.compile("edition", re.IGNORECASE)
        sizePattern = re.compile("([\d\.,]+\s*x\s*[\d\.,]+\s*x \s*[\d\.,]+)\s*cm", re.IGNORECASE)
        sizePattern2 = re.compile("([\d,\.]+\s*x\s*[\d,\.]+)\s*cm", re.IGNORECASE)
        sizePattern3 = re.compile("([\d,\.]+)\s*cm", re.IGNORECASE)
        estimatePattern = re.compile("(\w{3})\s+([\d\.,]+\s+\-\s+[\d\.,]+)", re.DOTALL)
        soldforPattern = re.compile("([\d\.,]+)\s+\w{3}", re.DOTALL)
        soldforPattern2 = re.compile("\w{3}\s+([\d\.,]+)", re.DOTALL)
        datePattern = re.compile("(\d{2}\s+\w+\s+\d{4})", re.DOTALL)
        yearPattern = re.compile("(\d{4})")
        birthdeathPattern = re.compile("(\d{4})\s*-?\s*(\d{0,4})")
        numberPattern = re.compile("(\d+)")
        beginspacePattern = re.compile("^\s+")
        beginparaPattern = re.compile("^\)\s*")
        endnumberPattern = re.compile("\s*\d+\s*$")
        brPattern = re.compile("<br\s*\/?>", re.IGNORECASE|re.DOTALL)
        matcatdict_en = {}
        matcatdict_fr = {}
        with open("/root/artwork/deploydirnew/docs/fineart_materials.csv", newline='') as mapfile:
        #with open("docs/fineart_materials.csv", newline='') as mapfile:
            mapreader = csv.reader(mapfile, delimiter=",", quotechar='"')
            for maprow in mapreader:
                matcatdict_en[maprow[1]] = maprow[3]
                matcatdict_fr[maprow[2]] = maprow[3]
        mapfile.close()
        articletags = soup.find_all("article", {'id' : 'katalog-detail'})
        if articletags.__len__() > 0:
            artistborntags = articletags[0].find_all("p", {'class' : 'artist-born'})
            if artistborntags.__len__() > 0:
                borncontents = artistborntags[0].renderContents().decode('utf-8')
                borncontents = borncontents.replace("–", "-")
                bps = re.search(birthdeathPattern, borncontents)
                if bps:
                    detailData['artist_birth'] = bps.groups()[0]
                    detailData['artist_death'] = bps.groups()[1]
            lotinfotags = articletags[0].find_all("p", {'class' : 'lot-info'})
            if lotinfotags.__len__() > 0:
                lotinfo = lotinfotags[0].renderContents().decode('utf-8')
                lotinfoparts = re.split(brPattern, lotinfo)
                for lotinfocontent in lotinfoparts:
                    lotinfocontent = lotinfocontent.replace(" ", " ")
                    lotinfocontent = lotinfocontent.replace("×", "x")
                    zps = re.search(sizePattern, lotinfocontent)
                    if zps and 'artwork_measurements_height' not in detailData.keys():
                        size = zps.groups()[0]
                        sizeparts = size.split("x")
                        if sizeparts.__len__() == 1:
                            detailData['artwork_measurements_height'] = sizeparts[0]
                        elif sizeparts.__len__() == 2:
                            detailData['artwork_measurements_height'] = sizeparts[0]
                            detailData['artwork_measurements_width'] = sizeparts[1]
                        elif sizeparts.__len__() == 3:
                            detailData['artwork_measurements_height'] = sizeparts[0]
                            detailData['artwork_measurements_width'] = sizeparts[1]
                            detailData['artwork_measurements_depth'] = sizeparts[2]
                        detailData['artwork_size_notes'] = size + " cm"
                        detailData['auction_measureunit'] = "cm"
                    zps2 = re.search(sizePattern2, lotinfocontent)
                    if zps2 and 'artwork_measurements_height' not in detailData.keys():
                        size = zps2.groups()[0]
                        sizeparts = size.split("x")
                        if sizeparts.__len__() == 1:
                            detailData['artwork_measurements_height'] = sizeparts[0]
                        elif sizeparts.__len__() == 2:
                            detailData['artwork_measurements_height'] = sizeparts[0]
                            detailData['artwork_measurements_width'] = sizeparts[1]
                        elif sizeparts.__len__() == 3:
                            detailData['artwork_measurements_height'] = sizeparts[0]
                            detailData['artwork_measurements_width'] = sizeparts[1]
                            detailData['artwork_measurements_depth'] = sizeparts[2]
                        detailData['artwork_size_notes'] = size + " cm"
                        detailData['auction_measureunit'] = "cm"
                    zps3 = re.search(sizePattern3, lotinfocontent)
                    if zps3 and 'artwork_measurements_height' not in detailData.keys():
                        size = zps3.groups()[0]
                        sizeparts = size.split("x")
                        if sizeparts.__len__() == 1:
                            detailData['artwork_measurements_height'] = sizeparts[0]
                        elif sizeparts.__len__() == 2:
                            detailData['artwork_measurements_height'] = sizeparts[0]
                            detailData['artwork_measurements_width'] = sizeparts[1]
                        elif sizeparts.__len__() == 3:
                            detailData['artwork_measurements_height'] = sizeparts[0]
                            detailData['artwork_measurements_width'] = sizeparts[1]
                            detailData['artwork_measurements_depth'] = sizeparts[2]
                        detailData['artwork_size_notes'] = size + " cm"
                        detailData['auction_measureunit'] = "cm"
                    lotinfodotparts = lotinfocontent.split(".")
                    for lotinfodotpart in lotinfodotparts:
                        mps = re.search(mediumPattern, lotinfodotpart)
                        if mps and 'artwork_materials' not in detailData.keys():
                            detailData['artwork_materials'] = lotinfodotpart
                        """
                        sps = re.search(signedPattern, lotinfodotpart)
                        if sps and 'signature' not in detailData.keys():
                            detailData['signature'] = lotinfodotpart
                            detailData['signature'] = beginparaPattern.sub("", detailData['signature'])
                            detailData['signature'] = detailData['signature'].replace('"', "'")
                            detailData['signature'] = endnumberPattern.sub("", detailData['signature'])
                        """
                    lotinfonbspparts = lotinfocontent.split("&nbsp;")
                    for lotinfonbsppart in lotinfonbspparts:
                        eps = re.search(editionPattern, lotinfonbsppart)
                        if eps and 'artwork_edition' not in detailData.keys():
                            #detailData['artwork_edition'] = lotinfonbsppart
                            nps = re.search(numberPattern, lotinfonbsppart)
                            if nps:
                                detailData['artwork_edition'] = nps.groups()[0]
            provenancetags = articletags[0].find_all("p", {'class' : 'provenienz'})
            if provenancetags.__len__() > 0:
                provenancecontent = provenancetags[0].renderContents().decode('utf-8')
                provenancecontent = self.__class__.htmltagPattern.sub("", provenancecontent)
                provenancecontent = provenancecontent.replace("Provenance", "")
                detailData['artwork_provenance'] = provenancecontent
                detailData['artwork_provenance'] = detailData['artwork_provenance'].replace('"', "'")
            lotpricetags = articletags[0].find_all("p", {'class' : 'lot-price'})
            if lotpricetags.__len__() > 0:
                lotpricecontent = lotpricetags[0].renderContents().decode('utf-8')
                lotpricecontent = lotpricecontent.replace("–", "-")
                tps = re.search(estimatePattern, lotpricecontent)
                if tps and 'price_estimate_min' not in detailData.keys():
                    tpsg = tps.groups()
                    currency = tpsg[0]
                    estimate = tpsg[1]
                    estimate = estimate.replace(".", "")
                    estimateparts = estimate.split("-")
                    detailData['price_estimate_min'] = estimateparts[0]
                    if estimateparts.__len__() > 1:
                        detailData['price_estimate_max'] = estimateparts[1]
            statusptags = articletags[0].find_all("p", {'class' : 'status'})
            if statusptags.__len__() > 0:
                statuscontents = statusptags[0].renderContents().decode('utf-8')
                statuscontents = self.__class__.htmltagPattern.sub("", statuscontents)
                statuscontents = statuscontents.replace("&nbsp;", " ")
                pps = re.search(soldforPattern, statuscontents)
                if pps and 'price_sold' not in detailData.keys():
                    detailData['price_sold'] = pps.groups()[0]
            if 'price_sold' not in detailData.keys():
                pricedivtags = soup.find_all("p", {'class' : 'lot-price'})
                if pricedivtags.__len__() > 0:
                    pricecontents = pricedivtags[0].renderContents().decode('utf-8')
                    if not "–" in pricecontents and not "-" in pricecontents:
                        pps2 = re.search(soldforPattern2, pricecontents)
                        if pps2:
                            detailData['price_sold'] = pps2.groups()[0]
                            detailData['price_sold'] = detailData['price_sold'].replace(".", "")
            withdrawnPattern = re.compile("withdrawn", re.IGNORECASE|re.DOTALL)
            detailData['price_kind'] = "unknown"
            if ('price_sold' in detailData.keys() and re.search(withdrawnPattern, detailData['price_sold'])) or ('price_estimate_max' in detailData.keys() and re.search(withdrawnPattern, detailData['price_estimate_max'])):
                detailData['price_kind'] = "withdrawn"
            elif 'price_sold' in detailData.keys() and detailData['price_sold'] != "":
                detailData['price_kind'] = "price realized"
            elif 'price_estimate_max' in detailData.keys() and detailData['price_estimate_max'] != "":
                detailData['price_kind'] = "estimate"
            else:
                pass
            datetags = articletags[0].find_all("span", {'class' : 'auction-date'})
            if datetags.__len__() > 0:
                datecontents = datetags[0].renderContents().decode('utf-8')
                dps = re.search(datePattern, datecontents)
                if dps and 'auction_start_date' not in detailData.keys():
                    detailData['auction_start_date'] = dps.groups()[0]
                    detailData['auction_start_date'] = self.__class__.formatDate(detailData['auction_start_date'])
            detailData['auction_house_name'] = 'Grisebach'
            exhibitiontags = articletags[0].find_all("p", {'class' : 'ausstellungen'})
            if exhibitiontags.__len__() > 0:
                exhibitioncontent = exhibitiontags[0].renderContents().decode('utf-8')
                exhibitioncontent = self.__class__.htmltagPattern.sub("", exhibitioncontent)
                exhibitioncontent = exhibitioncontent.replace("Exhibition", "")
                detailData['artwork_exhibited'] = exhibitioncontent
                detailData['artwork_exhibited'] = detailData['artwork_exhibited'].replace('"', "'")
            imgtags = articletags[0].find_all("img", {'class' : 'listview'})
            if imgtags.__len__() > 0:
                defaultimageurl = baseUrl + "/" + imgtags[0]['src']
                imagename1 = self.getImagenameFromUrl(defaultimageurl)
                imagename1 = str(imagename1)
                imagename1 = imagename1.replace("b'", "").replace("'", "")
                auctiontitle = self.auctiontitle.replace(" ", "_")
                processedAuctionTitle = auctiontitle.replace(" ", "_")
                processedArtistName = artistname.replace(" ", "_")
                processedArtistName = unidecode.unidecode(processedArtistName)
                processedArtworkName = artworkname.replace(" ", "_")
                sublot_number = ""
                auction_number = self.saleno
                lot_number = lotno
                #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + auction_number + "__" + lot_number + "__" + sublot_number
                newname1 = auction_number + "__" + processedArtistName + "__" + str(lot_number) + "_a"
                #encryptedFilename = self.encryptFilename(newname1)
                encryptedFilename = newname1
                imagepathparts = defaultimageurl.split("/")
                defimageurl = "/".join(imagepathparts[:-2])
                encryptedFilename = str(encryptedFilename).replace("b'", "")
                encryptedFilename = str(encryptedFilename).replace("'", "")
                detailData['image1_name'] = str(encryptedFilename) + ".jpg"
                detailData['artwork_images1'] = defaultimageurl
                self.getImage(detailData['artwork_images1'], imagepath, downloadimages)
                if downloadimages == "1":
                    encryptedFilename = str(encryptedFilename) + "-a.jpg"
                    self.renameImageFile(imagepath, imagename1, encryptedFilename)
        thumbPattern = re.compile("thumbs")
        allultags = soup.find_all("ul", {'class' : thumbPattern})
        alternateimages = []
        if allultags.__len__() > 0:
            allimgtags = allultags[0].find_all("img")
            for imgtag in allimgtags:
                imgurl = baseUrl + "/" + imgtag['src']
                alternateimages.append(imgurl)
        imgctr = 2
        suffices = ["-b", "-c", "-d", "-e"]
        suffctr = 0
        for altimg in alternateimages:
            imagename = self.getImagenameFromUrl(altimg)
            imagename = str(imagename)
            imagename = imagename.replace("b'", "").replace("'", "")
            altimageparts = altimg.split("/")
            altimageurl = "/".join(altimageparts[:-2])
            auctiontitle = self.auctiontitle.replace(" ", "_")
            processedAuctionTitle = auctiontitle.replace(" ", "_")
            processedArtistName = artistname.replace(" ", "_")
            processedArtworkName = artworkname.replace(" ", "_")
            sublot_number = ""
            auction_number = self.saleno
            lot_number = lotno
            newname = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + auction_number + "__" + lot_number + "__" + sublot_number
            encryptedFilename = self.encryptFilename(newname)
            detailData['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
            detailData['artwork_images' + str(imgctr)] = altimg
            self.getImage(detailData['artwork_images' + str(imgctr)], imagepath, downloadimages)
            if downloadimages == "1":
                encryptedFilename = str(encryptedFilename) + suffices[suffctr] + ".jpg"
                self.renameImageFile(imagepath, imagename, encryptedFilename)
            imgctr += 1
            suffctr += 1
            if suffctr > 3:
                break
        if 'artwork_condition_in' not in detailData.keys():
            conditiontags = soup.find_all("p", {'class' : 'addition'})
            if conditiontags.__len__() > 0:
                conditioncontents = conditiontags[0].renderContents().decode('utf-8')
                conditioncontents = self.__class__.htmltagPattern.sub("", conditioncontents)
                detailData['artwork_condition_in'] = conditioncontents
        lotinfotags = soup.find_all("p", {'class' : 'lot-info'})
        if lotinfotags.__len__() > 0:
            lotinfocontents = lotinfotags[0].renderContents().decode('utf-8')
            if 'artwork_condition_in' in detailData.keys():
                lotinfocontents = lotinfocontents + detailData['artwork_condition_in']
            detailData['artwork_description'] = lotinfocontents
            detailData['artwork_description'] = detailData['artwork_description'].replace("PROVENANCE", "<br><strong>Provenance</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("LITERATURE", "<br><strong>Literature</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("EXHIBITED", "<br><strong>Exhibited</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("Condition Report", "<br><strong>Condition Report</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("Notes:", "<br><strong>Notes:</strong><br>")
        if 'artwork_description' in detailData.keys():
            detailData['artwork_description'] = "<strong><br>Description<br></strong>" + detailData['artwork_description']
            detailData['artwork_description'] = detailData['artwork_description'].replace('"', "'")
            detailData['artwork_description'] = detailData['artwork_description'].replace("\n", " ").replace("\r", "")
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
        if 'artwork_condition_in' not in detailData.keys():
            conditiontags = soup.find_all("p", {'class' : 'addition'})
            if conditiontags.__len__() > 0:
                conditioncontents = conditiontags[0].renderContents().decode('utf-8')
                conditioncontents = self.__class__.htmltagPattern.sub("", conditioncontents)
                conditioncontents = conditioncontents.replace("\n", "").replace("\r", "")
                conditioncontents = conditioncontents.replace('"', "'")
                detailData['artwork_condition_in'] = conditioncontents
        if 'artwork_condition_in' in detailData.keys():
            detailData['artwork_condition_in'] = detailData['artwork_condition_in'].replace("\n", "").replace("\r", "")
            detailData['artwork_condition_in'] = detailData['artwork_condition_in'].replace('"', "'")
        return detailData


    def getImage(self, imageUrl, imagepath, downloadimages):
        imageUrlParts = imageUrl.split("/")
        imagefilename = imageUrlParts[-2] + "_" + imageUrlParts[-1]
        imagedir = imageUrlParts[-2]
        if downloadimages == "1":
            pageRequest = urllib.request.Request(imageUrl, headers=self.httpHeaders)
            pageResponse = None
            try:
                print("Opening image...")
                pageResponse = self.opener.open(pageRequest)
                print("Opened image...")
            except:
                print ("Error: %s"%sys.exc_info()[1].__str__())
            try:
                imageContent = pageResponse.read()
                print("Read image...")
                ifp = open(imagepath + os.path.sep + imagefilename, "wb")
                ifp.write(imageContent)
                ifp.close()
            except:
                print("Error: %s"%sys.exc_info()[1].__str__())
        return imagefilename


    def getInfoFromLotsData(self, htmlList, imagepath, downloadimages):
        baseUrl = "https://www.grisebach.com"
        info = []
        endSpacePattern = re.compile("\s+$", re.DOTALL)
        yearPattern = re.compile("(\d{4})")
        titlePattern = re.compile("”(.*?)”")
        for htmldiv in htmlList:
            data = {}
            data['auction_num'] = self.saleno
            lotno = ""
            data['artist_name'] = ""
            data['artwork_name'] = ""
            htmlContent = htmldiv.renderContents().decode('utf-8')
            s = BeautifulSoup(htmlContent, features="html.parser")
            anchortags = s.find_all("a")
            detailUrl = ""
            if anchortags.__len__() > 0:
                detailUrl = baseUrl + "/" + anchortags[0]['href']
            data['LOTURL'] = detailUrl
            lotnotags = s.find_all("strong", {'class' : 'lot-nr'})
            if lotnotags.__len__() > 0:
                lotno = lotnotags[0].renderContents().decode('utf-8')
            data['lot_num'] = lotno
            h2tags = s.find_all("h2", {'class' : 'artist-name'})
            if h2tags.__len__() > 0:
                data['artist_name'] = h2tags[0].renderContents().decode('utf-8')
            titledivtags = s.find_all("div", {'class' : 'title-wrapper'})
            if titledivtags.__len__() > 0:
                data['artwork_name'] = titledivtags[0].renderContents().decode('utf-8')
                data['artwork_name'] = data['artwork_name'].replace('"', "'")
                tps = re.search(titlePattern, data['artwork_name'])
                if tps:
                    data['artwork_name'] = tps.groups()[0]
                data['artwork_name'] = data['artwork_name'].replace("”", "")
                yps = re.search(yearPattern, data['artwork_name'])
                if yps:
                    yearfrom = yps.groups()[0]
                    data['artwork_start_year'] = yearfrom
                    data['artwork_name'] = yearPattern.sub("", data['artwork_name'])
            if not lotno:
                continue
            if detailUrl == "":
                continue
            data['lot_origin_url'] = detailUrl
            print("Getting '%s'..."%detailUrl)
            detailsPageContent = self.getDetailsPage(detailUrl)
            detailData = self.parseDetailPage(detailsPageContent, lotno, imagepath, downloadimages, data['artwork_name'], data['artist_name'])
            for k in detailData.keys():
                data[k] = detailData[k]
            data['auction_name'] = self.auctiontitle
            data['auction_location'] = "Berlin"
            if 'price_estimate_min' in data.keys():
                data['price_estimate_min'] = data['price_estimate_min'].replace(",", "").replace(" ", "")
            if 'price_estimate_max' in data.keys():
                data['price_estimate_max'] = data['price_estimate_max'].replace(",", "").replace(" ", "")
            if 'price_sold' in data.keys():
                data['price_sold'] = data['price_sold'].replace(",", "").replace(" ", "")
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
    pageurl = pageurl = "http://216.137.189.57:8080/scrapers/finish/?scrapername=Grisebach&auctionnumber=%s&auctionurl=%s&scrapertype=2"%(auctionno, urllib.parse.quote(auctionurl))
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
    grisebach = GrisebachBot(auctionurl, auctionnumber)
    fp = open(csvpath, "w")
    fieldnames = ['auction_house_name', 'auction_location', 'auction_num', 'auction_start_date', 'auction_end_date', 'auction_name', 'lot_num', 'sublot_num', 'price_kind', 'price_estimate_min', 'price_estimate_max', 'price_sold', 'artist_name', 'artist_birth', 'artist_death', 'artist_nationality', 'artwork_name', 'artwork_year_identifier', 'artwork_start_year', 'artwork_end_year', 'artwork_materials', 'artwork_category', 'artwork_markings', 'artwork_edition', 'artwork_description', 'artwork_measurements_height', 'artwork_measurements_width', 'artwork_measurements_depth', 'artwork_size_notes', 'auction_measureunit', 'artwork_condition_in', 'artwork_provenance', 'artwork_exhibited', 'artwork_literature', 'artwork_images1', 'artwork_images2', 'artwork_images3', 'artwork_images4', 'artwork_images5', 'image1_name', 'image2_name', 'image3_name', 'image4_name', 'image5_name', 'lot_origin_url']
    fieldsstr = ",".join(fieldnames)
    fp.write(fieldsstr + "\n")
    pagectr = 1
    while True:
        soup = BeautifulSoup(grisebach.currentPageContent, features="html.parser")
        lotsdata = grisebach.getLotsFromPage()
        info = grisebach.getInfoFromLotsData(lotsdata, imagepath, downloadimages)
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
        navigationdivtags = soup.find_all("div", {'class' : 'row katalog-list-navigation'})
        if navigationdivtags.__len__() > 0:
            allanchortags = navigationdivtags[0].find_all("a")
            found = 0
            for anchortag in allanchortags:
                anchorcontent = anchortag.renderContents().decode('utf-8')
                if anchorcontent == "Next":
                    found = 1
                    nextpageUrl = grisebach.baseUrl + anchortag['href']
                    grisebach.pageRequest = urllib.request.Request(nextpageUrl, headers=grisebach.httpHeaders)
                    try:
                        grisebach.pageResponse = grisebach.opener.open(grisebach.pageRequest)
                    except:
                        print("Couldn't find the page %s"%str(pagectr))
                        break
                    grisebach.currentPageContent = grisebach.__class__._decodeGzippedContent(grisebach.getPageContent())
            if not found:
                break
        else:
            break
    fp.close()
    updatestatus(auctionnumber, auctionurl)

# Example: python grisebach.py "https://www.grisebach.com/en/buy/catalogues/list-view.html?id=1990&L=1&katalog%5Bkat_id%5D=716&katalog%5Bsorting%5D=lot&katalog%5Blot_status%5D=all" 716 /home/supmit/work/art2/grisebach_716.csv /home/supmit/work/art2/images/grisebach/716 0 0


# supmit

