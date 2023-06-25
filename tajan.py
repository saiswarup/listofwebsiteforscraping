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


class TajanBot(object):
    
    startUrl=r"https://www.tajan.com/auction-catalog/modern-art_OH64A0G02J?pageNum=1"
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
        retdate = dd + "-" + monstr + "-" + year[2:]
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
        allh1tags = soup.find_all("h1", {'id' : 'catalogTitle'})
        if allh1tags.__len__() > 0:
            title = allh1tags[0].renderContents().decode('utf-8')
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


    def parseDetailPage(self, detailsPage, artistname, auction_number, lot_number, imagepath, downloadimages):
        baseUrl = "https://auction.tajan.com"
        detailData = {}
        soup = BeautifulSoup(detailsPage, features="html.parser")
        detailsparalist = soup.find_all("p", {'class' : 'mb-2'})
        if detailsparalist.__len__() == 0:
            return detailData
        mediumPattern = re.compile("(gold)|(silver)|(brass)|(bronze)|(wood)|(porcelain)|(stone)|(marble)|(metal)|(steel)|(iron)|(glass)|(plexiglas)|(chromogenic)|(paper)|(canvas)|(masonite)|(newsprint)|(silkscreen)|(parchment)|(linen)|(inkjet)|(ink\s+jet)|(pigment)|(\stin\s)|(photogravure)|(^oil\s+)|(\s+panel\s+)|(terracotta)|(ivory)|(\s+oak\s+)|(^oak\s+)|(\s+oak$)|(alabaster)", re.DOTALL|re.IGNORECASE)
        nonenglishmediumPattern = re.compile("(crayon)|(encre)|(plume)|(plume\s+et\s+encre)|(papier)|(pastel)|(craie)|(gouachée)|(aquarelle)|(lithographique)|(plomb)|(huile)|(cuivre)|(toile)|(bronze)|(Plâtre)|(en\s+terre\s+de\s+faïence)", re.IGNORECASE|re.DOTALL)
        signedPattern = re.compile("Signé", re.IGNORECASE)
        editionPattern = re.compile("édition", re.IGNORECASE)
        editionPattern2 = re.compile("Numéroté", re.IGNORECASE)
        sizePattern = re.compile("(Haut\.?\s*\d+\s*cm)", re.IGNORECASE)
        sizePattern2 = re.compile("([\d,]+\s*x\s*[\d,]+\s*cm)", re.IGNORECASE)
        sizePattern3 = re.compile("([\d,]+\s*cm)", re.IGNORECASE)
        sizeunitPattern = re.compile("\s*cm$", re.IGNORECASE)
        matcatdict_en = {}
        matcatdict_fr = {}
        #with open("docs/fineart_materials.csv", newline='') as mapfile:
        with open("/root/artwork/deploydirnew/docs/fineart_materials.csv", newline='') as mapfile:
            mapreader = csv.reader(mapfile, delimiter=",", quotechar='"')
            for maprow in mapreader:
                matcatdict_en[maprow[1]] = maprow[3]
                matcatdict_fr[maprow[2]] = maprow[3]
        mapfile.close()
        beginspacePattern = re.compile("^\s+")
        paracontent = detailsparalist[0].renderContents().decode('utf-8')
        paraparts = re.split("<br\s?\/?>", paracontent)
        yearPattern = re.compile("(\d{4})")
        endcommaPattern = re.compile(",\s*$", re.DOTALL)
        ctr = 0
        for para in paraparts:
            if ctr == 1:
                para = para.replace('\n', " ")
                para = para.replace('\r', " ")
                para = para.replace('"', "'")
                detailData['artwork_name'] = para
                detailData['artwork_name'] = beginspacePattern.sub("", detailData['artwork_name'])
                yps = re.search(yearPattern, detailData['artwork_name'])
                if yps:
                    detailData['artwork_start_year'] = yps.groups()[0]
                    detailData['artwork_name'] = yearPattern.sub("", detailData['artwork_name'])
                    detailData['artwork_name'] = endcommaPattern.sub("", detailData['artwork_name'])
            mneps = re.search(nonenglishmediumPattern, para)
            if mneps:
                para = para.replace('\n', " ")
                para = para.replace('\r', " ")
                para = para.replace('"', "'")
                detailData['artwork_materials'] = para
                detailData['artwork_materials'] = beginspacePattern.sub("", detailData['artwork_materials'])
            mps = re.search(mediumPattern, para)
            if 'artwork_materials' not in detailData.keys() and mps:
                para = para.replace('\n', " ")
                para = para.replace('\r', " ")
                para = para.replace('"', "'")
                detailData['artwork_materials'] = para
                detailData['artwork_materials'] = beginspacePattern.sub("", detailData['artwork_materials'])
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
            eps = re.search(editionPattern, para)
            if eps:
                para = para.replace('\n', " ")
                para = para.replace('\r', " ")
                para = para.replace('"', "'")
                detailData['artwork_edition'] = para
            eps2 = re.search(editionPattern2, para)
            if eps2 and 'artwork_edition' not in detailData.keys():
                para = para.replace('\n', " ")
                para = para.replace('\r', " ")
                para = para.replace('"', "'")
                detailData['artwork_edition'] = para
            zps = re.search(sizePattern, para)
            if zps and 'artwork_measurements_height' not in detailData.keys():
                size = zps.groups()[0]
                size = size.replace("\n", " ")
                size = size.replace("\r", " ")
                size = beginspacePattern.sub("", size)
                size = size.lower()
                size = size.replace(",", ".")
                sizewithoutunit = sizeunitPattern.sub("", size)
                sizeparts = sizewithoutunit.split("x")
                detailData['artwork_measurements_height'] = sizeparts[0]
                if sizeparts.__len__() > 1:
                    detailData['artwork_measurements_width'] = sizeparts[1]
                if sizeparts.__len__() > 2:
                    detailData['artwork_measurements_depth'] = sizeparts[2]
                detailData['auction_measureunit'] = "cm"
                detailData['artwork_size_notes'] = size
            zps2 = re.search(sizePattern2, para)
            if zps2 and 'artwork_measurements_height' not in detailData.keys():
                size = zps2.groups()[0]
                size = size.replace("\n", " ")
                size = size.replace("\r", " ")
                size = beginspacePattern.sub("", size)
                size = size.lower()
                size = size.replace(",", ".")
                sizewithoutunit = sizeunitPattern.sub("", size)
                sizeparts = sizewithoutunit.split("x")
                detailData['artwork_measurements_height'] = sizeparts[0]
                if sizeparts.__len__() > 1:
                    detailData['artwork_measurements_width'] = sizeparts[1]
                if sizeparts.__len__() > 2:
                    detailData['artwork_measurements_depth'] = sizeparts[2]
                detailData['auction_measureunit'] = "cm"
                detailData['artwork_size_notes'] = size
            zps3 = re.search(sizePattern3, para)
            if zps3 and 'artwork_measurements_height' not in detailData.keys():
                size = zps3.groups()[0]
                size = size.replace("\n", " ")
                size = size.replace("\r", " ")
                size = beginspacePattern.sub("", size)
                size = size.lower()
                size = size.replace(",", ".")
                sizewithoutunit = sizeunitPattern.sub("", size)
                sizeparts = sizewithoutunit.split("x")
                detailData['artwork_measurements_height'] = sizeparts[0]
                if sizeparts.__len__() > 1:
                    detailData['artwork_measurements_width'] = sizeparts[1]
                if sizeparts.__len__() > 2:
                    detailData['artwork_measurements_depth'] = sizeparts[2]
                detailData['auction_measureunit'] = "cm"
                detailData['artwork_size_notes'] = size
            ctr += 1
        #imgtags = soup.find_all("img", {'class' : 'xzoom'})
        imgtags = soup.find_all("img", {'itemprop' : 'image'})
        if imgtags.__len__() == 0:
             imageanchortags = soup.find_all("a", {'data-zoom-id' : 'magicLotCarousel'})
             if imageanchortags.__len__() > 0:
                 imagenetpath = imageanchortags[0]['href']
             else:
                 imagenetpath = ""
        else:
            imagenetpath = imgtags[0]['src']
        #print(imagenetpath)
        imagename1 = self.getImagenameFromUrl(imagenetpath)
        imagename1 = str(imagename1)
        imagename1 = imagename1.replace("b'", "").replace("'", "")
        auctiontitle = self.auctiontitle.replace(" ", "_")
        processedAuctionTitle = auctiontitle.replace(" ", "_")
        processedArtistName = artistname.replace(" ", "_")
        processedArtistName = unidecode.unidecode(processedArtistName)
        #processedArtworkName = detailData['artwork_name'].replace(" ", "_")
        sublot_number = ""
        #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + auction_number + "__" + lot_number + "__" + sublot_number
        newname1 = auction_number + "__" + processedArtistName + "__" + str(lot_number) + "_a"
        #encryptedFilename = self.encryptFilename(newname1)
        encryptedFilename = newname1
        imagepathparts = imagenetpath.split("/")
        defimageurl = "/".join(imagepathparts[:-2])
        encryptedFilename = str(encryptedFilename).replace("b'", "")
        encryptedFilename = str(encryptedFilename).replace("'", "")
        detailData['image1_name'] = str(encryptedFilename) + ".jpg"
        detailData['artwork_images1'] = imagenetpath
        self.getImage(detailData['artwork_images1'], imagepath, downloadimages)
        if downloadimages == "1":
            encryptedFilename = str(encryptedFilename) + "-a.jpg"
            self.renameImageFile(imagepath, imagename1, encryptedFilename)
        classPattern = re.compile("carousel-mobile-item")
        allimgdivs = soup.find_all("div", {'class' : classPattern})
        alternateimgs = []
        imgctr = 2
        for imgdiv in allimgdivs:
            imgtags = imgdiv.find_all("img")
            if imgtags.__len__() == 0:
                 continue
            altimg = imgtags[0]['src']
            if altimg != detailData['artwork_images1']:
                alternateimgs.append(altimg)
        if alternateimgs.__len__() == 0:
            for anchortag in imageanchortags:
                alternateimgs.append(anchortag['href'])
        if alternateimgs.__len__() > 0:
            altimage2 = alternateimgs[0]
            altimage2parts = altimage2.split("/")
            altimageurl = "/".join(altimage2parts[:-2])
            processedArtistName = artistname.replace(" ", "_")
            processedArtistName = unidecode.unidecode(processedArtistName)
            #processedArtworkName = detailData['artwork_name'].replace(" ", "_")
            sublot_number = ""
            #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + auction_number + "__" + lot_number + "__" + sublot_number
            newname1 = auction_number + "__" + processedArtistName + "__" + str(lot_number) + "_b"
            #encryptedFilename = self.encryptFilename(newname1)
            encryptedFilename = newname1
            detailData['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
            detailData['artwork_images' + str(imgctr)] = altimage2
            self.getImage(detailData['artwork_images' + str(imgctr)], imagepath, downloadimages)
            if downloadimages == "1":
                encryptedFilename = str(encryptedFilename) + "-b.jpg"
                self.renameImageFile(imagepath, imagename1, encryptedFilename)
            imgctr += 1
        if alternateimgs.__len__() > 1:
            altimage3 = alternateimgs[1]
            altimage3parts = altimage3.split("/")
            altimageurl = "/".join(altimage3parts[:-2])
            detailData['image' + str(imgctr) + '_name'] = self.getImagenameFromUrl(altimage3)
            processedArtistName = artistname.replace(" ", "_")
            processedArtistName = unidecode.unidecode(processedArtistName)
            #processedArtworkName = detailData['artwork_name'].replace(" ", "_")
            sublot_number = ""
            #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + auction_number + "__" + lot_number + "__" + sublot_number
            newname1 = auction_number + "__" + processedArtistName + "__" + str(lot_number) + "_c"
            #encryptedFilename = self.encryptFilename(newname1)
            encryptedFilename = newname1
            detailData['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
            detailData['artwork_images' + str(imgctr)] = altimage3
            self.getImage(detailData['artwork_images' + str(imgctr)], imagepath, downloadimages)
            if downloadimages == "1":
                encryptedFilename = str(encryptedFilename) + "-c.jpg"
                self.renameImageFile(imagepath, imagename1, encryptedFilename)
            imgctr += 1
        if alternateimgs.__len__() > 2:
            altimage4 = alternateimgs[2]
            altimage4parts = altimage4.split("/")
            altimageurl = "/".join(altimage4parts[:-2])
            detailData['image' + str(imgctr) + '_name'] = self.getImagenameFromUrl(altimage4)
            processedArtistName = artistname.replace(" ", "_")
            processedArtistName = unidecode.unidecode(processedArtistName)
            #processedArtworkName = detailData['artwork_name'].replace(" ", "_")
            sublot_number = ""
            #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + auction_number + "__" + lot_number + "__" + sublot_number
            newname1 = auction_number + "__" + processedArtistName + "__" + str(lot_number) + "_d"
            #encryptedFilename = self.encryptFilename(newname1)
            encryptedFilename = newname1
            detailData['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
            detailData['artwork_images' + str(imgctr)] = altimage4
            self.getImage(detailData['artwork_images' + str(imgctr)], imagepath, downloadimages)
            if downloadimages == "1":
                encryptedFilename = str(encryptedFilename) + "-d.jpg"
                self.renameImageFile(imagepath, imagename1, encryptedFilename)
            imgctr += 1
        if alternateimgs.__len__() > 3:
            altimage5 = alternateimgs[3]
            altimage5parts = altimage5.split("/")
            altimageurl = "/".join(altimage5parts[:-2])
            detailData['image' + str(imgctr) + '_name'] = self.getImagenameFromUrl(altimage5)
            processedArtistName = artistname.replace(" ", "_")
            processedArtistName = unidecode.unidecode(processedArtistName)
            #processedArtworkName = detailData['artwork_name'].replace(" ", "_")
            sublot_number = ""
            #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + auction_number + "__" + lot_number + "__" + sublot_number
            newname1 = auction_number + "__" + processedArtistName + "__" + str(lot_number) + "_e"
            #encryptedFilename = self.encryptFilename(newname1)
            encryptedFilename = newname1
            detailData['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
            detailData['artwork_images' + str(imgctr)] = altimage5
            self.getImage(detailData['artwork_images' + str(imgctr)], imagepath, downloadimages)
            if downloadimages == "1":
                encryptedFilename = str(encryptedFilename) + "-e.jpg"
                self.renameImageFile(imagepath, imagename1, encryptedFilename)
            imgctr += 1
        detailslilist = soup.find_all("li", {'class' : 'mb-2'})
        if  detailslilist.__len__() == 0:
            detailsdivtags = soup.find_all("p", {'class' : 'mb-2'})
            if detailsdivtags.__len__() > 0:
                detailsdivcontents = detailsdivtags[0].renderContents().decode('utf-8')
                detailsdivcontents = self.__class__.htmltagPattern.sub("", detailsdivcontents)
                detailsdivcontents = detailsdivcontents.replace("\n", " ").replace("\r", " ")
                detailData['artwork_description'] = detailsdivcontents
            descultags = soup.find_all('ul', {'class' : 'list-unstyled'})
            if descultags.__len__() > 0 and ('artwork_description' not in detailData.keys() or detailData['artwork_description'] == ""):
                desccontents = descultags[0].renderContents().decode('utf-8')
                detailData['artwork_description'] += desccontents
                detailData['artwork_description'] = detailData['artwork_description'].strip()
                detailData['artwork_description'] = self.__class__.htmltagPattern.sub("", detailData['artwork_description'])
                detailData['artwork_description'] = detailData['artwork_description'].replace("\n", " ")
                detailData['artwork_description'] = detailData['artwork_description'].replace("\r", " ")
                detailData['artwork_description'] = detailData['artwork_description'].replace('"', "'")
                detailData['artwork_description'] = detailData['artwork_description'].replace("PROVENANCE", "<br><strong>Provenance</strong><br>")
                detailData['artwork_description'] = detailData['artwork_description'].replace("LITERATURE", "<br><strong>Literature</strong><br>")
                detailData['artwork_description'] = detailData['artwork_description'].replace("EXHIBITED", "<br><strong>Exhibited</strong><br>")
                detailData['artwork_description'] = detailData['artwork_description'].replace("EXPOSITIONS", "<br><strong>Expositions</strong><br>")
                detailData['artwork_description'] = detailData['artwork_description'].replace("BIBLIOGRAPHIE", "<br><strong>Literature</strong><br>")
                detailData['artwork_description'] = detailData['artwork_description'].replace("Condition Report", "<br><strong>Condition Report</strong><br>")
                detailData['artwork_description'] = detailData['artwork_description'].replace("Notes:", "<br><strong>Notes:</strong><br>")
            if 'artwork_description' in detailData.keys():
                detailData['artwork_description'] = "<strong><br>Description<br></strong>" + detailData['artwork_description']
                print(detailData['artwork_description'])
            auctiondateSpanTags = soup.find_all("div", {'class' : 'dateTime'})
            if auctiondateSpanTags.__len__() > 0:
                auctiondateSpan = auctiondateSpanTags[0]
                auctiondate = auctiondateSpan.renderContents().decode('utf-8')
                auctiondate = beginspacePattern.sub("", auctiondate)
                self.auctiondate = auctiondate
                detailData['auction_start_date'] = self.__class__.formatDate(auctiondate)
            return detailData
        detailscontent = detailslilist[0].renderContents().decode('utf-8')
        detailsparts = re.split("<br\s?\/?>\s*<br\s?\/?>", detailscontent)
        provenancePattern = re.compile("PROVENANCE", re.IGNORECASE|re.DOTALL)
        exhibitionPattern = re.compile("EXPOSITIONS", re.IGNORECASE|re.DOTALL)
        literaturePattern = re.compile("BIBLIOGRAPHIE", re.IGNORECASE|re.DOTALL)
        #beginspacePattern = re.compile("^\s+")
        for dpart in detailsparts:
            pps = re.search(provenancePattern, dpart)
            if pps:
                detailData['artwork_provenance'] = dpart
                detailData['artwork_provenance'] = detailData['artwork_provenance'].replace('"', "'")
                detailData['artwork_provenance'] = detailData['artwork_provenance'].replace('\n', " ")
                detailData['artwork_provenance'] = detailData['artwork_provenance'].replace('\r', " ")
                detailData['artwork_provenance'] = self.__class__.htmltagPattern.sub("", detailData['artwork_provenance'])
                provenancecomponents = detailData['artwork_provenance'].split("BIBLIOGRAPHIE")
                if provenancecomponents.__len__() > 1:
                    for provcomp in provenancecomponents:
                        if re.search(provenancePattern, provcomp):
                            if re.search(exhibitionPattern, provcomp):
                                provcompparts = provcomp.split("EXPOSITIONS")
                                for provcomppart in provcompparts:
                                    if re.search(provenancePattern, provcomppart):
                                        provcomp = provcomppart
                                        break
                            detailData['artwork_provenance'] = provcomp
                detailData['artwork_provenance'] = detailData['artwork_provenance'].replace('PROVENANCE', "").replace("Notes:", "")
                detailData['artwork_provenance'] = beginspacePattern.sub("", detailData['artwork_provenance'])
            eps = re.search(exhibitionPattern, dpart)
            if eps:
                detailData['artwork_exhibited'] = dpart
                detailData['artwork_exhibited'] = detailData['artwork_exhibited'].replace('"', "'")
                detailData['artwork_exhibited'] = detailData['artwork_exhibited'].replace('\n', " ")
                detailData['artwork_exhibited'] = detailData['artwork_exhibited'].replace('\r', " ")
                detailData['artwork_exhibited'] = self.__class__.htmltagPattern.sub("", detailData['artwork_exhibited'])
                exhibitioncomponents = detailData['artwork_exhibited'].split("BIBLIOGRAPHIE")
                if exhibitioncomponents.__len__() > 1:
                    for exhibcomp in exhibitioncomponents:
                        if re.search(exhibitionPattern, exhibcomp):
                            if re.search(provenancePattern, exhibcomp):
                                exhibcompparts = exhibcomp.split("PROVENANCE")
                                for exhibcomppart in exhibcompparts:
                                    if re.search(exhibitionPattern, exhibcomppart):
                                        exhibcomp = exhibcomppart
                                        break
                            detailData['artwork_exhibited'] = exhibcomp
                detailData['artwork_exhibited'] = detailData['artwork_exhibited'].replace('EXPOSITIONS', "")
                detailData['artwork_exhibited'] = beginspacePattern.sub("", detailData['artwork_exhibited'])
            lps = re.search(literaturePattern, dpart)
            if lps:
                detailData['artwork_literature'] = dpart
                detailData['artwork_literature'] = detailData['artwork_literature'].replace('"', "'")
                detailData['artwork_literature'] = detailData['artwork_literature'].replace('\n', " ")
                detailData['artwork_literature'] = detailData['artwork_literature'].replace('\r', " ")
                detailData['artwork_literature'] = self.__class__.htmltagPattern.sub("", detailData['artwork_literature'])
                literaturecomponents = detailData['artwork_literature'].split("EXPOSITIONS")
                if literaturecomponents.__len__() > 1:
                    for litcomp in literaturecomponents:
                        if re.search(literaturePattern, litcomp):
                            if re.search(provenancePattern, litcomp):
                                litcompparts = litcomp.split("PROVENANCE")
                                for litcomppart in litcompparts:
                                    if re.search(literaturePattern, litcomppart):
                                        litcomp = litcomppart
                                        break
                            detailData['artwork_literature'] = litcomp
                detailData['artwork_literature'] = detailData['artwork_literature'].replace('BIBLIOGRAPHIE', "")
                detailData['artwork_literature'] = beginspacePattern.sub("", detailData['artwork_literature'])
        detailsdivtags = soup.find_all("p", {'class' : 'mb-2'})
        if detailsdivtags.__len__() > 0:
            detailsdivcontents = detailsdivtags[0].renderContents().decode('utf-8')
            detailsdivcontents = self.__class__.htmltagPattern.sub("", detailsdivcontents)
            detailsdivcontents = detailsdivcontents.replace("\n", " ").replace("\r", " ")
            detailData['artwork_description'] = detailsdivcontents
        descultags = soup.find_all('ul', {'class' : 'list-unstyled'})
        if descultags.__len__() > 0 and ('artwork_description' not in detailData.keys() or detailData['artwork_description'] == ""):
            desccontents = descultags[0].renderContents().decode('utf-8')
            detailData['artwork_description'] += desccontents
            detailData['artwork_description'] = detailData['artwork_description'].strip()
            detailData['artwork_description'] = self.__class__.htmltagPattern.sub("", detailData['artwork_description'])
            detailData['artwork_description'] = detailData['artwork_description'].replace("\n", " ")
            detailData['artwork_description'] = detailData['artwork_description'].replace("\r", " ")
            detailData['artwork_description'] = detailData['artwork_description'].replace('"', "'")
            detailData['artwork_description'] = detailData['artwork_description'].replace("PROVENANCE", "<br><strong>Provenance</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("LITERATURE", "<br><strong>Literature</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("EXHIBITED", "<br><strong>Exhibited</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("EXPOSITIONS", "<br><strong>Expositions</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("BIBLIOGRAPHIE", "<br><strong>Literature</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("Condition Report", "<br><strong>Condition Report</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("Notes:", "<br><strong>Notes:</strong><br>")
        if 'artwork_description' in detailData.keys():
            detailData['artwork_description'] = "<strong><br>Description<br></strong>" + detailData['artwork_description']
            print(detailData['artwork_description'])
        auctiondateSpanTags = soup.find_all("div", {'class' : 'dateTime'})
        if auctiondateSpanTags.__len__() > 0:
            auctiondateSpan = auctiondateSpanTags[0]
            auctiondate = auctiondateSpan.renderContents().decode('utf-8')
            auctiondate = beginspacePattern.sub("", auctiondate)
            self.auctiondate = auctiondate
            detailData['auction_start_date'] = self.__class__.formatDate(auctiondate)
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
        baseUrl = "https://www.tajan.com"
        info = []
        endSpacePattern = re.compile("\s+$", re.DOTALL)
        soldpricePattern = re.compile("([\d\s\.,]+)\s+€")
        beginspacePattern = re.compile("^\s+")
        bsoup = BeautifulSoup(self.currentPageContent, features="html.parser")
        locdivtags = bsoup.find_all("div", {'id' : 'auctionPanelInfo'})
        locationinfo = ""
        if locdivtags.__len__() > 0:
            locptags = locdivtags[0].find_all("p", {'class' : 'mb-0'})
            if locptags.__len__() > 0:
                locationinfo = locptags[0].renderContents().decode('utf-8')
                locationinfo = locationinfo.replace("Localisation: ", "")
                locationinfo = locationinfo.replace("Location: ", "")
                locationparts = locationinfo.split(",")
                location = locationparts[0]
        for htmldiv in htmlList:
            data = {}
            data['auction_num'] = self.saleno
            data['auction_location'] = location
            lotno = ""
            htmlContent = htmldiv.renderContents().decode('utf-8')
            s = BeautifulSoup(htmlContent, features="html.parser")
            allanchors = s.find_all("a")
            htmlanchor = allanchors[0]
            detailUrl = baseUrl + htmlanchor['href']
            data['lot_origin_url'] = detailUrl
            anchorcontent = htmlanchor.renderContents().decode('utf-8')
            infoPattern = re.compile("^\s*(\d+):\s+([^\(\)]+)\s+\((\d{4})\s*\-?\s*(\d{0,4})", re.DOTALL)
            ips = re.search(infoPattern, anchorcontent)
            if ips:
                ipsg = ips.groups()
                lotno = ipsg[0]
                data['lot_num'] = lotno
                data['artist_name'] = ipsg[1]
                data['artist_birth'] = ipsg[2]
                data['artist_death'] = ipsg[3]
            else:
                altPattern1 = re.compile("^\s*(\d+):\s+([^\d]+)\s+(\d{4})", re.DOTALL)
                altPattern2 = re.compile("^\s*(\d+):\s+([\w\s\(\)]+)\s+\((\d{4})\s*\-?\s*(\d{0,4})\)", re.DOTALL)
                altPattern3 = re.compile("^\s*(\d+):\s+\*?\[?([\w\s’'\-\.]+)\]?", re.DOTALL)
                aps1 = re.search(altPattern1, anchorcontent)
                aps2 = re.search(altPattern2, anchorcontent)
                aps3 = re.search(altPattern3, anchorcontent)
                if aps1:
                    apsg1 = aps1.groups()
                    lotno = apsg1[0]
                    data['lot_num'] = lotno
                    data['artist_name'] = apsg1[1]
                    data['artist_birth'] = apsg1[2]
                    data['artist_death'] = ""
                elif aps2:
                    apsg2 = aps2.groups()
                    lotno = apsg2[0]
                    data['lot_num'] = lotno
                    data['artist_name'] = apsg2[1]
                    data['artist_birth'] = apsg2[2]
                    data['artist_death'] = apsg2[3]
                elif aps3:
                    apsg3 = aps3.groups()
                    lotno = apsg3[0]
                    data['lot_num'] = lotno
                    data['artist_name'] = apsg3[1]
                    data['artist_birth'] = ""
                    data['artist_death'] = ""
            if 'artist_name' in data.keys():
                data['artist_name'] = data['artist_name'].replace(" (née en", "").replace(" (né en", "")
                data['artist_name'] = data['artist_name'].replace("¤ ", "")
                data['artist_name'] = data['artist_name'].replace('"', "'")
                data['artist_name'] = data['artist_name'].replace("\n", "").replace("\r", "")
            data['auction_house_name'] = 'Tajan'
            estimatep = htmldiv.findNext("p")
            estimatecontent =  estimatep.renderContents().decode('utf-8')
            estimatecontent = estimatecontent.replace("\n", "").replace("\r", "").replace("€", "").replace("Estimation:", "")
            estimatecontent = re.compile("\s+", re.DOTALL).sub("", estimatecontent)
            estimatecontentparts = estimatecontent.split("-")
            data['price_estimate_min'] = estimatecontentparts[0]
            data['price_estimate_max'] = estimatecontentparts[1]
            estimatecontent = estimatecontentparts[0] + " - " + estimatecontentparts[1]
            data['price_estimate_min'] = data['price_estimate_min'].replace("Estimate:", "")
            data['price_estimate_max'] = data['price_estimate_max'].replace("Estimate:", "")
            data['price_estimate_min'] = data['price_estimate_min'] # + " EUR"
            data['price_estimate_max'] = data['price_estimate_max'] # + " EUR"
            solddiv = htmldiv.findNext("div", {'class' : 'realized mb-2'})
            data['price_sold'] = ""
            if solddiv:
                solddivcontents = solddiv.renderContents().decode('utf-8')
                solddivcontents = self.htmltagPattern.sub("", solddivcontents)
                spps = re.search(soldpricePattern, solddivcontents)
                if spps:
                    soldprice = spps.groups()[0]
                    data['price_sold'] = soldprice # + " EUR"
                    data['price_sold'] = beginspacePattern.sub("", data['price_sold'])
                    data['price_sold'] = data['price_sold'].replace(" ", "")
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
            #print(data['lot_num'] + " ## " + data['artist_name'] + " ## " + data['artist_birth'] + " ## " + data['artist_death'] + " ## " + data['price_estimate_max'])
            print("Getting '%s'... lot # '%s'"%(data['lot_origin_url'], str(lotno)))
            detailsPageContent = self.getDetailsPage(detailUrl)
            if not lotno:
                continue
            detailData = self.parseDetailPage(detailsPageContent, data['artist_name'], self.saleno, lotno, imagepath, downloadimages)
            for k in detailData.keys():
                data[k] = detailData[k]
            if 'price_sold' not in data.keys() or data['price_sold'] == "":
                data['price_sold'] = ""
            data['auction_start_date'] = self.__class__.formatDate(self.auctiondate)
            data['auction_start_date'] = data['auction_start_date'].replace("\n", " ").replace("\r\n", " ")
            if 'price_estimate_min' in data.keys():
                data['price_estimate_min'] = data['price_estimate_min'].replace(",", "").replace(" ", "")
            if 'price_estimate_max' in data.keys():
                data['price_estimate_max'] = data['price_estimate_max'].replace(",", "").replace(" ", "")
            if 'price_sold' in data.keys():
                data['price_sold'] = data['price_sold'].replace(",", "").replace(" ", "")
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
    pageurl = "http://216.137.189.57:8080/scrapers/finish/?scrapername=Tajan&auctionnumber=%s&auctionurl=%s&scrapertype=2"%(auctionno, urllib.parse.quote(auctionurl))
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
    tajan = TajanBot(auctionurl, auctionnumber)
    fp = open(csvpath, "w")
    fieldnames = ['auction_house_name', 'auction_location', 'auction_num', 'auction_start_date', 'auction_end_date', 'auction_name', 'lot_num', 'sublot_num', 'price_kind', 'price_estimate_min', 'price_estimate_max', 'price_sold', 'artist_name', 'artist_birth', 'artist_death', 'artist_nationality', 'artwork_name', 'artwork_year_identifier', 'artwork_start_year', 'artwork_end_year', 'artwork_materials', 'artwork_category', 'artwork_markings', 'artwork_edition', 'artwork_description', 'artwork_measurements_height', 'artwork_measurements_width', 'artwork_measurements_depth', 'artwork_size_notes', 'auction_measureunit', 'artwork_condition_in', 'artwork_provenance', 'artwork_exhibited', 'artwork_literature', 'artwork_images1', 'artwork_images2', 'artwork_images3', 'artwork_images4', 'artwork_images5', 'image1_name', 'image2_name', 'image3_name', 'image4_name', 'image5_name', 'lot_origin_url']
    fieldsstr = ",".join(fieldnames)
    fp.write(fieldsstr + "\n")
    pagectr = 1
    while True:
        soup = BeautifulSoup(tajan.currentPageContent, features="html.parser")
        lotsdata = tajan.getLotsFromPage()
        info = tajan.getInfoFromLotsData(lotsdata, imagepath, downloadimages)
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
            nextpageUrl = tajan.baseUrl[:-1] + nextpageanchors[0]['href']
            tajan.pageRequest = urllib.request.Request(nextpageUrl, headers=tajan.httpHeaders)
            try:
                tajan.pageResponse = tajan.opener.open(tajan.pageRequest)
            except:
                print("Couldn't find the page %s"%str(pagectr))
                break
            tajan.currentPageContent = tajan.__class__._decodeGzippedContent(tajan.getPageContent())
        else:
            break
    fp.close()
    updatestatus(auctionnumber, auctionurl)

# Example: python tajan.py https://www.tajan.com/auction-catalog/modern-art_OH64A0G02J?pageNum=1 2108 /home/supmit/work/art2/tajan_2108.csv /home/supmit/work/art2/images/tajan/2108 0 0

# Example: python tajan.py https://www.tajan.com/auction-catalog/Contemporary-Art_WT1R9JM40J/ 2118 /home/supmit/work/art2/tajan_2118.csv /home/supmit/work/art2/images/tajan/2118 0 0


# supmit

