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
    return content


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


class CheffinsBot(object):
    
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
        return cookies

    _getCookieFromResponse = classmethod(_getCookieFromResponse)


    def getPageContent(self):
        return self.pageResponse.read()


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
        baseurl = "https://www.cheffins.co.uk"
        pageContent = self.currentPageContent
        soup = BeautifulSoup(pageContent, features="html.parser")
        allh1tags = soup.find_all("h1")
        if allh1tags.__len__() > 0:
            title = allh1tags[0].renderContents().decode('utf-8')
            title = title.replace("\n", "").replace("\r", "")
            title = self.__class__.htmltagPattern.sub("", title)
            beginspacePattern = re.compile("^\s+")
            endspacePattern = re.compile("\s+$")
            title = beginspacePattern.sub("", title)
            title = endspacePattern.sub("", title)
            self.auctiontitle = title
        lotblocks = soup.find_all("div", {'class' : 'auction-lot'})
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


    def renameImageFile(self, basepath, imagefilename, mappedImagename):
        oldfilename = basepath + "/" + imagefilename
        newfilename = basepath + "/" + mappedImagename
        newfilename = newfilename.replace("'", "")
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


    def parseDetailPage(self, detailsPage, artistname, auction_number, lot_number, imagepath, downloadimages):
        baseUrl = "https://www.cheffins.co.uk"
        detailData = {}
        soup = BeautifulSoup(detailsPage, features="html.parser")
        #mediumPattern = re.compile("(gold)|(silver)|(brass)|(bronze)|(wood)|(porcelain)|(stone)|(marble)|(metal)|(steel)|(iron)|(glass)|(plexiglas)|(chromogenic)|(paper)|(canvas)|(masonite)|(newsprint)|(silkscreen)|(parchment)|(linen)|(inkjet)|(ink\s+jet)|(pigment)|(\stin\s)|(photogravure)|(^oil\s+)|(\s+panel\s+)|(terracotta)|(ivory)|(\s+oak\s+)|(^oak\s+)|(\s+oak$)|(alabaster)", re.DOTALL|re.IGNORECASE)
        mediumPattern = re.compile("(oil\s+on\s+canvas)|(etchings?\s+on\s+canvas)|(etchings?\s+on\s+paper)|(oil\s+on\s+board)|(oil\s+on\s+panel)|(gouache\s+on\s+paper)|(pencil\s+on\s+paper)|(watercolou?r\s+on\s+buff\s+paper)|(watercolou?r\s+on\s+paper)|(pastel\s+on\s+laid\s+paper)|(pastel\s+on\s+paper)|(watercolou?r\s+on\s+ivory)|(watercolou?rs\s+on\s+paper)|(charcoal\s+heightened\s+with\s+white\s+chalk\s+on\s+brown\s+paper)|(charcoal\s+on\s+\w*\s*paper)|(chalk\s+on\s+board)|(charcoal\s+on\s+board)|(charcoal\s+on\s+panel)|(charcoal\s+on\s+canvas)", re.DOTALL|re.IGNORECASE)
        nonenglishmediumPattern = re.compile("(crayon)|(encre)|(plume)|(plume\s+et\s+encre)|(papier)|(pastel)|(craie)|(gouachée)|(aquarelle)|(lithographique)|(plomb)|(huile)|(cuivre)|(toile)|(bronze)|(Plâtre)|(en\s+terre\s+de\s+faïence)", re.IGNORECASE|re.DOTALL)
        editionPattern = re.compile("édition", re.IGNORECASE)
        editionPattern2 = re.compile("Numéroté", re.IGNORECASE)
        markingsPattern = re.compile("(signed)|(inscribed)", re.IGNORECASE)
        sizePattern = re.compile("Haut\.?\s*([\d\.,]+)\s*cm", re.IGNORECASE)
        sizePattern2 = re.compile("([\d,\.]+\s*x\s*[\d,\.]+)\s*cm", re.IGNORECASE)
        sizePattern3 = re.compile("([\d,\.]+)\s*cm", re.IGNORECASE)
        sizeunitPattern = re.compile("\s*cm$", re.IGNORECASE)
        conditionPattern = re.compile("condition\s+report", re.IGNORECASE)
        artworknamePattern1 = re.compile("\)(.*?)signed\s+", re.IGNORECASE)
        artworknamePattern2 = re.compile("\)(.*?)[\d\.]+\s*x", re.IGNORECASE)
        artworknamePattern3 = re.compile("century(.*?)[\d\.]+\s+x", re.IGNORECASE)
        nonnamePattern = re.compile("(watercolou?r)|(inscribed)", re.IGNORECASE)
        matcatdict_en = {}
        matcatdict_fr = {}
        artworkname = ""
        #with open("docs/fineart_materials.csv", newline='') as mapfile:
        with open("/root/artwork/deploydirnew/docs/fineart_materials.csv", newline='') as mapfile:
            mapreader = csv.reader(mapfile, delimiter=",", quotechar='"')
            for maprow in mapreader:
                matcatdict_en[maprow[1]] = maprow[3]
                matcatdict_fr[maprow[2]] = maprow[3]
        mapfile.close()
        beginspacePattern = re.compile("^\s+")
        dateclassPattern = re.compile("ki\-date")
        datePattern1 = re.compile("(\d{1,2}\s+\w{3})\s+\+\s+(\d{1,2}\s+\w{3}\s+\d{4})")
        datePattern2 = re.compile("(\d{1,2}\s+\w{3}\s+\d{4})")
        brPattern = re.compile("<br\s*\/?>", re.IGNORECASE)
        spacePattern = re.compile("^\s*$")
        datedivtags = soup.find_all("div", {'class' : dateclassPattern})
        if datedivtags.__len__() > 0:
            datecontents = datedivtags[0].renderContents().decode('utf-8')
            datecontents = datecontents.replace("\n", "").replace("\r", "")
            dps1 = re.search(datePattern1, datecontents)
            dps2 = re.search(datePattern2, datecontents)
            if dps1:
                date1 = dps1.groups()[0]
                date2 = dps1.groups()[1]
                dateparts = date2.split(" ")
                if dateparts.__len__() > 2:
                    date1 += " " + dateparts[2]
                date1 = date1.replace(" ", "-")
                date2 = date2.replace(" ", "-")
                detailData['auction_start_date'] = date1
                detailData['auction_end_date'] = date2
            elif dps2:
                date1 = dps2.groups()[0]
                date1 = date1.replace(" ", "-")
                detailData['auction_start_date'] = date1
        desch2tags = soup.find_all("h2", {'id' : 'fulldesc'})
        if desch2tags.__len__() > 0:
            descptag = desch2tags[0].findNext("p")
            descpcontents = descptag.renderContents().decode('utf-8')
            descpcontents = descpcontents.replace("\n", "").replace("\r", "")
            detailData['artwork_description'] = descpcontents
            detailData['artwork_description'] = self.__class__.htmltagPattern.sub("", detailData['artwork_description'])
            detailData['artwork_description'] = detailData['artwork_description'].replace("\n", " ")
            detailData['artwork_description'] = detailData['artwork_description'].replace("\r", " ")
            detailData['artwork_description'] = detailData['artwork_description'].replace('"', "'")
            detailData['artwork_description'] = detailData['artwork_description'].replace("Provenance:", "<br><strong>Provenance</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("Literature:", "<br><strong>Literature</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("Exhibited:", "<br><strong>Exhibited</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("Condition Report", "<br><strong>Condition Report</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("Notes:", "<br><strong>Notes:</strong><br>")
            zps = re.search(sizePattern, descpcontents)
            if zps and 'artwork_measurements_height' not in detailData.keys():
                size = zps.groups()[0]
                detailData['artwork_measurements_height'] = size
                detailData['artwork_size_notes'] = str(size) + " cm"
                detailData['auction_measureunit'] = "cm"
            zps2 = re.search(sizePattern2, descpcontents)
            if zps2 and 'artwork_measurements_height' not in detailData.keys():
                size = zps2.groups()[0]
                sizeparts = size.split("x")
                if sizeparts.__len__() > 0:
                    detailData['artwork_measurements_height'] = sizeparts[0]
                    detailData['artwork_measurements_width'] = sizeparts[1]
                detailData['artwork_size_notes'] = str(size) + " cm"
                detailData['auction_measureunit'] = "cm"
            zps3 = re.search(sizePattern3, descpcontents)
            if zps3 and 'artwork_measurements_height' not in detailData.keys():
                size = zps3.groups()[0]
                detailData['artwork_measurements_height'] = size
                detailData['artwork_size_notes'] = str(size) + " cm"
                detailData['auction_measureunit'] = "cm"
            descparts = descpcontents.split("Exhibited:")
            if descparts.__len__() > 1:
                exhibitiontext = descparts[1]
                exhibitionparts = exhibitiontext.split("CONDITION")
                if exhibitionparts.__len__() > 1:
                    conditiontext = exhibitionparts[1]
                    exhibitiontext = exhibitionparts[0]
                    detailData['artwork_condition_in'] = conditiontext
                detailData['artwork_exhibited'] = exhibitiontext
            elif 'artwork_condition_in' not in detailData.keys():
                descparts = descpcontents.split("CONDITION")
                if descparts.__len__() > 1:
                    conditiontext = descparts[1]
                    detailData['artwork_condition_in'] = conditiontext
            descparts = descpcontents.split("Provenance:")
            if descparts.__len__() > 1:
                provenancetext = descparts[1]
                provenanceparts = provenancetext.split("CONDITION")
                if provenanceparts.__len__() > 1:
                    conditiontext = provenanceparts[1]
                    provenancetext = provenanceparts[0]
                    detailData['artwork_condition_in'] = conditiontext
                detailData['artwork_provenance'] = provenancetext
                provenanceparts = provenancetext.split("Literature:")
                if provenanceparts.__len__() > 1:
                    literaturetext = provenanceparts[1]
                    provenancetext = provenanceparts[0]
                    detailData['artwork_literature'] = literaturetext
                detailData['artwork_provenance'] = provenancetext
            elif 'artwork_condition_in' not in detailData.keys():
                descparts = descpcontents.split("CONDITION")
                if descparts.__len__() > 1:
                    conditiontext = descparts[1]
                    detailData['artwork_condition_in'] = conditiontext
            conditionparts = re.split(conditionPattern, descpcontents)
            if conditionparts.__len__() > 1 and 'artwork_condition_in' not in detailData.keys():
                detailData['artwork_condition_in'] = conditionparts[1]
            descpcomponents = re.split(brPattern, descpcontents)
            artname = descpcomponents[0] # Keep this value. If we don't find a name for the lot from the regular place, we will use this.
            for descpcomponent in descpcomponents:
                descpcomponent = beginspacePattern.sub("", descpcomponent)
                mps = re.search(mediumPattern, descpcomponent)
                if mps and 'artwork_materials' not in detailData.keys():
                    detailData['artwork_materials'] = descpcomponent
                kps = re.search(markingsPattern, descpcomponent)
                if kps and 'artwork_markings' not in detailData.keys():
                    descpcomponent = descpcomponent.replace('"', "'")
                    detailData['artwork_markings'] = descpcomponent
            anps1 = re.search(artworknamePattern1, descpcontents)
            anps2 = re.search(artworknamePattern2, descpcontents)
            anps3 = re.search(artworknamePattern3, descpcontents)
            if anps1 and 'artwork_name' not in detailData.keys():
                detailData['artwork_name'] = anps1.groups()[0]
                detailData['artwork_name'] = self.__class__.htmltagPattern.sub("", detailData['artwork_name'])
                artworkname = detailData['artwork_name']
            elif anps2 and 'artwork_name' not in detailData.keys():
                detailData['artwork_name'] = anps2.groups()[0]
                detailData['artwork_name'] = mediumPattern.sub("", detailData['artwork_name'])
                detailData['artwork_name'] = self.__class__.htmltagPattern.sub("", detailData['artwork_name'])
                artworkname = detailData['artwork_name']
            elif anps3 and 'artwork_name' not in detailData.keys():
                detailData['artwork_name'] = anps3.groups()[0]
                detailData['artwork_name'] = mediumPattern.sub("", detailData['artwork_name'])
                detailData['artwork_name'] = self.__class__.htmltagPattern.sub("", detailData['artwork_name'])
                artworkname = detailData['artwork_name']
            else:
                pass
            if 'artwork_name' not in detailData.keys() or re.search(nonnamePattern, detailData['artwork_name']):
                artname = self.__class__.htmltagPattern.sub("", artname)
                artname = artname.title()
                arttitletags = soup.find_all("title")
                if arttitletags.__len__() > 0: # Prefer the string in page title tag to the title extracted from the description.
                    titlename = arttitletags[0].renderContents().decode('utf-8')
                    titlename = titlename.replace(" in - Cheffins Fine Art", "")
                    if artistname not in titlename:
                        artname = titlename
                detailData['artwork_name'] = artname
                artworkname = detailData['artwork_name']
        #print(detailData['artwork_name'])
        avcardPattern = re.compile("av\-card", re.DOTALL)
        avcarddivtags = soup.find_all("div", {'class' : 'av-cardWrap'})
        if avcarddivtags.__len__() == 0:
            avcarddivtags = soup.find_all("div", {'class' : avcardPattern})
        if avcarddivtags.__len__() == 0:
            if 'artwork_description' in detailData.keys():
                detailData['artwork_description'] = "<strong><br>Description<br></strong>" + detailData['artwork_description']
            detailData['artwork_images1'], detailData['artwork_images2'], detailData['artwork_images3'] = "", "", ""
            detailData['image1_name'], detailData['image2_name'], detailData['image3_name'] = "", "", ""
            return detailData
        allimgtags = avcarddivtags[0].find_all("img")
        if allimgtags.__len__() == 0:
            if 'artwork_description' in detailData.keys():
                detailData['artwork_description'] = "<strong><br>Description<br></strong>" + detailData['artwork_description']
            detailData['artwork_images1'], detailData['artwork_images2'], detailData['artwork_images3'] = "", "", ""
            detailData['image1_name'], detailData['image2_name'], detailData['image3_name'] = "", "", ""
            return detailData
        imagenetpath = allimgtags[0]['src']
        imagename1 = self.getImagenameFromUrl(imagenetpath)
        imagename1 = str(imagename1)
        imagename1 = imagename1.replace("b'", "").replace("'", "")
        auctiontitle = self.auctiontitle.replace(" ", "_")
        processedAuctionTitle = auctiontitle.replace(" ", "_")
        processedArtistName = artistname.replace(" ", "_")
        processedArtistName = unidecode.unidecode(processedArtistName)
        processedArtworkName = artworkname.replace(" ", "_")
        sublot_number = ""
        #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + auction_number + "__" + lot_number + "__" + sublot_number
        newname1 = auction_number + "__" + processedArtistName + "__" + lot_number + "_a"
        #encryptedFilename = self.encryptFilename(newname1)
        encryptedFilename = newname1
        imagepathparts = imagenetpath.split("/")
        defimageurl = "/".join(imagepathparts[:-2])
        detailData['image1_name'] = encryptedFilename + ".jpg"
        detailData['artwork_images1'] = imagenetpath
        if downloadimages == "1":
            self.getImage(detailData['artwork_images1'], imagepath, downloadimages)
            encryptedFilename = str(encryptedFilename) + "-a.jpg"
            encryptedFilename = encryptedFilename.replace("b'", "").replace("'", "")
            self.renameImageFile(imagepath, imagename1, encryptedFilename)
        alternateimgs = []
        imgctr = 2
        for imgtag in allimgtags[1:]:
            if not imgtag:
                continue
            try:
                altimg = imgtag['src']
                if altimg != detailData['artwork_images1']:
                    alternateimgs.append(altimg)
            except:
                pass
        if alternateimgs.__len__() > 0:
            altimage2 = alternateimgs[0]
            altimage2parts = altimage2.split("/")
            altimageurl = "/".join(altimage2parts[:-2])
            processedArtistName = artistname.replace(" ", "_")
            processedArtistName = unidecode.unidecode(processedArtistName)
            processedArtworkName = artworkname.replace(" ", "_")
            sublot_number = ""
            #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + auction_number + "__" + lot_number + "__" + sublot_number
            newname1 = auction_number + "__" + processedArtistName + "__" + lot_number + "_b"
            #encryptedFilename = self.encryptFilename(newname1)
            encryptedFilename = newname1
            detailData['image' + str(imgctr) + '_name'] = encryptedFilename + ".jpg"
            detailData['artwork_images' + str(imgctr)] = altimage2
            if downloadimages == "1":
                self.getImage(detailData['artwork_images' + str(imgctr)], imagepath, downloadimages)
                encryptedFilename = str(encryptedFilename) + "-b.jpg"
                encryptedFilename = encryptedFilename.replace("b'", "").replace("'", "")
                encryptedFilename = encryptedFilename.replace("'", "")
                self.renameImageFile(imagepath, imagename1, encryptedFilename)
            imgctr += 1
        if alternateimgs.__len__() > 1:
            altimage3 = alternateimgs[1]
            altimage3parts = altimage3.split("/")
            altimageurl = "/".join(altimage3parts[:-2])
            detailData['image' + str(imgctr) + '_name'] = self.getImagenameFromUrl(altimage3)
            processedArtistName = artistname.replace(" ", "_")
            processedArtistName = unidecode.unidecode(processedArtistName)
            processedArtworkName = artworkname.replace(" ", "_")
            sublot_number = ""
            #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + auction_number + "__" + lot_number + "__" + sublot_number
            newname1 = auction_number + "__" + processedArtistName + "__" + lot_number + "_c"
            #encryptedFilename = self.encryptFilename(newname1)
            encryptedFilename = newname1
            detailData['image' + str(imgctr) + '_name'] = encryptedFilename + ".jpg"
            detailData['artwork_images' + str(imgctr)] = altimage3
            if downloadimages == "1":
                self.getImage(detailData['artwork_images' + str(imgctr)], imagepath, downloadimages)
                encryptedFilename = str(encryptedFilename) + "-c.jpg"
                encryptedFilename = encryptedFilename.replace("b'", "").replace("'", "")
                encryptedFilename = encryptedFilename.replace("'", "")
                self.renameImageFile(imagepath, imagename1, encryptedFilename)
            imgctr += 1
        if alternateimgs.__len__() > 2:
            altimage4 = alternateimgs[2]
            altimage4parts = altimage4.split("/")
            altimageurl = "/".join(altimage4parts[:-2])
            detailData['image' + str(imgctr) + '_name'] = self.getImagenameFromUrl(altimage4)
            processedArtistName = artistname.replace(" ", "_")
            processedArtistName = unidecode.unidecode(processedArtistName)
            processedArtworkName = artworkname.replace(" ", "_")
            sublot_number = ""
            #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + auction_number + "__" + lot_number + "__" + sublot_number
            newname1 = auction_number + "__" + processedArtistName + "__" + lot_number + "_d"
            #encryptedFilename = self.encryptFilename(newname1)
            encryptedFilename = newname1
            detailData['image' + str(imgctr) + '_name'] = encryptedFilename + ".jpg"
            detailData['artwork_images' + str(imgctr)] = altimage4
            if downloadimages == "1":
                self.getImage(detailData['artwork_images' + str(imgctr)], imagepath, downloadimages)
                encryptedFilename = str(encryptedFilename) + "-d.jpg"
                encryptedFilename = encryptedFilename.replace("b'", "").replace("'", "")
                encryptedFilename = encryptedFilename.replace("'", "")
                self.renameImageFile(imagepath, imagename1, encryptedFilename)
            imgctr += 1
        if alternateimgs.__len__() > 3:
            altimage5 = alternateimgs[3]
            altimage5parts = altimage5.split("/")
            altimageurl = "/".join(altimage5parts[:-2])
            detailData['image' + str(imgctr) + '_name'] = self.getImagenameFromUrl(altimage5)
            processedArtistName = artistname.replace(" ", "_")
            processedArtistName = unidecode.unidecode(processedArtistName)
            processedArtworkName = artworkname.replace(" ", "_")
            sublot_number = ""
            #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + auction_number + "__" + lot_number + "__" + sublot_number
            newname1 = auction_number + "__" + processedArtistName + "__" + lot_number + "_e"
            #encryptedFilename = self.encryptFilename(newname1)
            encryptedFilename = newname1
            detailData['image' + str(imgctr) + '_name'] = encryptedFilename + ".jpg"
            detailData['artwork_images' + str(imgctr)] = altimage5
            if downloadimages == "1":
                self.getImage(detailData['artwork_images' + str(imgctr)], imagepath, downloadimages)
                encryptedFilename = str(encryptedFilename) + "-e.jpg"
                encryptedFilename = encryptedFilename.replace("b'", "").replace("'", "")
                encryptedFilename = encryptedFilename.replace("'", "")
                self.renameImageFile(imagepath, imagename1, encryptedFilename)
            imgctr += 1
        if 'artwork_description' in detailData.keys():
            detailData['artwork_description'] = "<strong><br>Description<br></strong>" + detailData['artwork_description']
        detailData['auction_house_name'] = "Cheffin's"
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
        """
        if 'artwork_markings' in detailData.keys():
            print(detailData['artwork_markings'])
        if 'artwork_materials' in detailData.keys():
            print(detailData['artwork_materials'])
        """
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


    def getInfoFromLotsData(self, htmlList, imagepath, downloadimages):
        baseUrl = "https://www.cheffins.co.uk"
        info = []
        endSpacePattern = re.compile("\s+$", re.DOTALL)
        soldpricePattern = re.compile("([\d\s\.,]+)\s+€")
        beginspacePattern = re.compile("^\s+")
        lotnoPattern = re.compile("Lot\s*(\d+)")
        soldpricelabelPattern = re.compile("Sold\s+for", re.IGNORECASE|re.DOTALL)
        estimatelabelPattern = re.compile("Estimate", re.IGNORECASE|re.DOTALL)
        titlePattern1 = re.compile("([\w\s,\.é']+)\s+\((\w+),\s+[\w\.\s]*(\d{4})[–-]{1}(\d{4})\)")
        titlePattern2 = re.compile("([\w\s\*]+),?\s+([\w\s\.]*\d{2}th\s+century)", re.IGNORECASE|re.DOTALL)
        titlePattern3 = re.compile("([\w\s,']+),\s+circa\s+(\d{4})", re.IGNORECASE|re.DOTALL)
        titlePattern4 = re.compile("([\w\s,']+)\s+(\d{4}),$", re.IGNORECASE|re.DOTALL)
        titlePattern5 = re.compile("([\w\s,']+)", re.IGNORECASE|re.DOTALL)
        winePattern = re.compile("(\s+port\s+)|(whisky)|(\s+wine\s+)|(cognac)|(Chateau)", re.IGNORECASE)
        yearPattern = re.compile("(\d{4})")
        artdescPattern = re.compile("^An?\s+[a-zA-Z\d]+")
        nonnamePattern = re.compile("(watercolou?r)|(inscribed)", re.IGNORECASE)
        titledivPattern = re.compile("al\-title")
        for htmldiv in htmlList:
            divcontents = htmldiv.renderContents().decode('utf-8')
            data = {}
            lotno = ""
            htmlurl = ""
            s = BeautifulSoup(divcontents, features="html.parser")
            lotnodivtags = s.find_all("div", {'class' : 'al-lotNumber'})
            if lotnodivtags.__len__() > 0:
                lotnocontents = lotnodivtags[0].renderContents().decode('utf-8')
                lotnocontents = self.__class__.htmltagPattern.sub("", lotnocontents)
                lotnocontents = lotnocontents.replace("\n", "").replace("\r", "")
                lps = re.search(lotnoPattern, lotnocontents)
                if lps:
                    lotno = lps.groups()[0]
                    data['lot_num'] = lotno
                else:
                    continue
            pricedivtags = s.find_all("div", {'class' : 'al-est'})
            if pricedivtags.__len__() > 0:
                pricedivcontents = pricedivtags[0].renderContents().decode('utf-8')
                pricedivcontents = self.__class__.htmltagPattern.sub("", pricedivcontents)
                pricedivcontents = pricedivcontents.replace("\n", "").replace("\r", "")
                spps = re.search(soldpricelabelPattern, pricedivcontents)
                epps = re.search(estimatelabelPattern, pricedivcontents)
                if spps:
                    soldpricegbpPattern = re.compile("£\s*([\d\.,]+)")
                    soldpriceusdPattern = re.compile("$\s*([\d\.,]+)")
                    spsg = re.search(soldpricegbpPattern, pricedivcontents)
                    spsu = re.search(soldpriceusdPattern, pricedivcontents)
                    if spsg:
                        price = spsg.groups()[0]
                        #data['price_sold'] = price + " GBP"
                        data['price_sold'] = price
                    elif spsu:
                        price = spsu.groups()[0]
                        #data['price_sold'] = price + " USD"
                        data['price_sold'] = price
                    else:
                        pass
                elif epps:
                    pass
                    # Write parsing logic for estimate computation
                else:
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
            titledivtags = s.find_all("div", {'class' : titledivPattern})
            if titledivtags.__len__() > 0:
                anchortags = titledivtags[0].find_all("a")
                if anchortags.__len__() > 0 and anchortags[0] is not None:
                    htmlurl = baseUrl + anchortags[0]['href']
                titlecontents = titledivtags[0].renderContents().decode('utf-8')
                titlecontents = titlecontents.replace("\n", "").replace("\r", "")
                titlecontents = self.__class__.htmltagPattern.sub("", titlecontents)
                tps1 = re.search(titlePattern1, titlecontents)
                tps2 = re.search(titlePattern2, titlecontents)
                tps3 = re.search(titlePattern3, titlecontents)
                tps4 = re.search(titlePattern4, titlecontents)
                tps5 = re.search(titlePattern5, titlecontents)
                if tps1 and 'artist_name' not in data.keys():
                    artistname = tps1.groups()[0]
                    data['artist_name'] = artistname
                    data['artist_nationality'] = tps1.groups()[1]
                    data['artist_birth'] = tps1.groups()[2]
                    data['artist_death'] = tps1.groups()[3]
                elif tps2 and 'artist_name' not in data.keys():
                    artistname = tps2.groups()[0]
                    data['artist_name'] = artistname
                    data['artwork_start_year'] = tps2.groups()[1]
                    data['artist_birth'] = ""
                    data['artist_death'] = ""
                elif tps3 and 'artist_name' not in data.keys():
                    artistname = tps3.groups()[0]
                    data['artist_name'] = artistname
                    data['artwork_start_year'] = tps3.groups()[1]
                    data['artist_birth'] = ""
                    data['artist_death'] = ""
                elif tps4 and 'artist_name' not in data.keys():
                    data['artwork_name'] = tps4.groups()[0]
                    data['artist_name'] = ""
                    data['artwork_start_year'] = tps4.groups()[1]
                    data['artist_birth'] = ""
                    data['artist_death'] = ""
                elif tps5 and 'artist_name' not in data.keys():
                    artistname = tps5.groups()[0]
                    wps = re.search(winePattern, artistname)
                    if wps: # looks like this is actually a wine of some sort
                        data['artwork_name'] = artistname
                        data['artist_name'] = ""
                        yps = re.search(yearPattern, artistname)
                        if yps:
                            data['artwork_start_year'] = yps.groups()[0]
                    else:
                        data['artist_name'] = artistname
                    data['artist_birth'] = ""
                    data['artist_death'] = ""
                else:
                    titlecontentparts = titlecontents.split(",")
                    if titlecontentparts.__len__() > 0:
                        data['artist_name'] = titlecontentparts[0]
                    elif titlecontentparts.__len__() > 1:
                        data['artist_name'] = titlecontentparts[0]
                        data['artwork_start_year'] = titlecontentparts[1]
                    else:
                        data['artist_name'] = ""
                if 'artist_name' in data.keys():
                    artistname = data['artist_name']
                    yps = re.search(yearPattern, artistname)
                    if yps:
                        data['artwork_start_year'] = yps.groups()[0]
                        data['artist_name'] = yearPattern.sub("", data['artist_name'])
            """
            try:
                print(data['lot_num'] + " ## " + data['artist_name'] + " ## " + data['artist_birth'] + " ## " + data['artist_death'] + " ## " + data['price_sold'])
            except:
                print(data['lot_num'] + " ## " + data['artist_name'])
            """
            data['lot_origin_url'] = htmlurl
            print("Getting '%s'..."%data['lot_origin_url'])
            detailsPageContent = self.getDetailsPage(htmlurl)
            detailData = self.parseDetailPage(detailsPageContent, data['artist_name'], self.saleno, lotno, imagepath, downloadimages)
            for k in detailData.keys():
                if k == 'artwork_name' and k in data.keys() and data[k] != "":
                    continue
                data[k] = detailData[k]
            if 'price_sold' not in data.keys() or data['price_sold'] == "":
                data['price_sold'] = ""
            if 'price_estimate_min' in data.keys():
                data['price_estimate_min'] = data['price_estimate_min'].replace(",", "").replace(" ", "")
            if 'price_estimate_max' in data.keys():
                data['price_estimate_max'] = data['price_estimate_max'].replace(",", "").replace(" ", "")
            if 'price_sold' in data.keys():
                data['price_sold'] = data['price_sold'].replace(",", "").replace(" ", "")
            data['auction_name'] = self.auctiontitle
            data['auction_num'] = self.saleno
            data['auction_location'] = "Cambridge"
            # Check if 'artist_name' starts with 'A ' or 'An '. If so, then we put that value in 'artwork_name'.
            if ('artwork_name' not in data.keys() or data['artwork_name'] == "") and 'artist_name' in data.keys():
                ads = re.search(artdescPattern, data['artist_name'])
                if ads and 'school' not in data['artist_name']: # The word 'school' doesn't exist in data['artist_name']
                    data['artwork_name'] = data['artist_name']
                    data['artist_name'] = ""
            if 'artwork_name' in data.keys():
                nnps = re.search(nonnamePattern, data['artwork_name']) # If the name doesn't look like a name, clear it.
                if nnps:
                    data['artwork_name'] = ""
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
    pageurl = "http://216.137.189.57:8080/scrapers/finish/?scrapername=Cheffins&auctionnumber=%s&auctionurl=%s&scrapertype=2"%(auctionno, urllib.parse.quote(auctionurl))
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
    cheffins = CheffinsBot(auctionurl, auctionnumber)
    fp = open(csvpath, "w")
    fieldnames = ['auction_house_name', 'auction_location', 'auction_num', 'auction_start_date', 'auction_end_date', 'auction_name', 'lot_num', 'sublot_num', 'price_kind', 'price_estimate_min', 'price_estimate_max', 'price_sold', 'artist_name', 'artist_birth', 'artist_death', 'artist_nationality', 'artwork_name', 'artwork_year_identifier', 'artwork_start_year', 'artwork_end_year', 'artwork_materials', 'artwork_category', 'artwork_markings', 'artwork_edition', 'artwork_description', 'artwork_measurements_height', 'artwork_measurements_width', 'artwork_measurements_depth', 'artwork_size_notes', 'auction_measureunit', 'artwork_condition_in', 'artwork_provenance', 'artwork_exhibited', 'artwork_literature', 'artwork_images1', 'artwork_images2', 'artwork_images3', 'artwork_images4', 'artwork_images5', 'image1_name', 'image2_name', 'image3_name', 'image4_name', 'image5_name', 'lot_origin_url']
    fieldsstr = ",".join(fieldnames)
    fp.write(fieldsstr + "\n")
    pagectr = 1
    last_lot_num = -1
    paginationblock = 6
    paginationstart = 0
    while True:
        soup = BeautifulSoup(cheffins.currentPageContent, features="html.parser")
        lotsdata = cheffins.getLotsFromPage()
        info = cheffins.getInfoFromLotsData(lotsdata, imagepath, downloadimages)
        if info.__len__() > 0 and info[-1]['lot_num'] == last_lot_num:
            break
        try:
            last_lot_num = info[-1]['lot_num']
        except:
            break # This could happen when we reach the end of the list of lots.
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
        if pagectr == paginationblock + paginationstart:
            paginationstart = paginationblock + paginationstart
        nextpageUrl = auctionurl + "?pg=%s&pgstart=%s"%(str(pagectr), str(paginationstart))
        cheffins.pageRequest = urllib.request.Request(nextpageUrl, headers=cheffins.httpHeaders)
        try:
            cheffins.pageResponse = cheffins.opener.open(cheffins.pageRequest)
        except:
            print("Couldn't find the page %s"%str(pagectr))
            break
        cheffins.currentPageContent = cheffins.__class__._decodeGzippedContent(cheffins.getPageContent())
    fp.close()
    updatestatus(auctionnumber, auctionurl)

# Example: python cheffins.py https://www.cheffins.co.uk/fine-art/catalogue-view,the-fine-sale_193.htm 193 /home/supmit/work/art2/cheffins_193.csv /home/supmit/work/art2/images/cheffins/193 0 0

# supmit

