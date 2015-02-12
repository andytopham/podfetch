#!/usr/bin/python
""" Pulls podcasts from the web and puts them in the destination dir."""
import feedparser
import time
import subprocess
import urllib
import logging
import datetime
import os
import shutil
import argparse
import pickle

LOGFILE='./log/podfetch.log'
DESTINATIONDIR = '/mnt/NAS/Buffalo/AApods'
LASTUPDATEDFILE = './lastupdated.pkl'

class podfetch:
	''' A class to fetch podcasts from the web and leave them ready for playing by mpd. '''
	
	def __init__(self):
		''' Setup the list of podcast feeds. '''
		self.podlist = [['TOTD ','http://downloads.bbc.co.uk/podcasts/radio4/totd/rss.xml',0],
					['MoreOrLess','http://downloads.bbc.co.uk/podcasts/radio4/moreorless/rss.xml',0],
					['TWIT ','http://feeds.twit.tv/twit',0],
					['TWIG ','http://leo.am/podcasts/twig',0],
					['TWICH','http://leo.am/podcasts/twich',0],
					['WindowsWkly','http://leoville.tv/podcasts/ww.xml',0],
					['Click','http://downloads.bbc.co.uk/podcasts/worldservice/digitalp/rss.xml',0],
					['SatdayEdtion','http://downloads.bbc.co.uk/podcasts/5live/jot/rss.xml',0],
					['TechTent','http://downloads.bbc.co.uk/podcasts/worldservice/tech/rss.xml',0],
					['IOT  ','http://downloads.bbc.co.uk/podcasts/radio4/iot/rss.xml',0],
					['TechStuff','http://www.howstuffworks.com/podcasts/techstuff.rss',0],
					['AmpHour','http://www.theamphour.com/feed/podcast',1],
					['Sprocket','http://www.thepodcasthost.com/thesprocketpodcast/feed/podcast/',1],
					['AstronomyCst','http://feeds.feedburner.com/astronomycast',1],
					['Which','http://feeds.feedburner.com/whichtechnology',1],
					['99%Invisible','http://feeds.99percentinvisible.org/99percentinvisible',1],
					['EmbeddedSys','http://embedded.fm/episodes?format=rss',1],
					['MarathonTalk','http://marathontalk.libsyn.com/rss',1],
					['PCPro','http://podcast.pcpro.co.uk/?feed=rss2',1],
					['CNet  ','http://www.cnet.co.uk/feeds/podcasts/',1],
					['IMtalk','http://ironmantalk.libsyn.com/rss',1],
					['Wired','http://www.wired.co.uk/podcast/rss',2]
					]
		self.testlist = [['TechStuff','http://www.howstuffworks.com/podcasts/techstuff.rss',0]
					]
		self.broken = [['ScienceTalk','http://www.scientificamerican.com/podcast/sciam_podcast_i.xml'],
					['Python', 'http://www.frompythonimportpodcast.com/episodes/', 1],
					['Geekwire','http://kiroradio.com/rss/podcast.php?s=1000',1]
					]
		self.htmlStatusCodes = {200: 'OK',
								301: 'Feed permanently moved.',
								302: 'Feed temporarily moved.',
								400: 'Bad request syntax',
								410: 'Feed gone! Need to change feed list.',
								500: 'Internal server error'
								}
		self.downloadCount = 0

	def feedType(self,urltuple):
		''' Open the feed list and find type. '''
		label,url = urltuple
		print "Fetching list: ",label
		logging.info("Fetching list: "+label)
		d = feedparser.parse(url)
		logging.info("Feed version:"+d.version)
		self.checkHtmlStatus(d.status)		
	
	def howOld(self,episode_date):
		'''Measure how old the feed is. Need to work in datetime, since need to subtract times.'''
		localtime_s = time.mktime(time.localtime(time.time()))
		last_time_s = time.mktime(episode_date)
		age_s = (localtime_s - last_time_s)
		age_days = age_s/60/60/24
		print 'Age: '+str(int(age_days))+' days.',
		logging.info('Age: '+str(int(age_days))+' days.')
		return(0)
		
	def checkHtmlStatus(self,feed):
		try:
			status = feed.status
		except:
			print "Bad feed."
			logging.warning("Feed has no returned status. Aborting.")
			return(1)
		logging.info("Feedparser status = "+str(status))
		if status in self.htmlStatusCodes:
			logging.info("Feed status:"+str(status)+' '+self.htmlStatusCodes[status])
		if status != 200:
			logging.info("Bad html status, abandoning feed")
			return(1)
		try:
			logging.info("Feed version = :"+feed.version)
			title=feed.channel.title
			first_entry = feed.entries[0]
			episode_date = first_entry.updated_parsed
			logging.info(title+' Last update: '+str(episode_date[0])+'/'+str(episode_date[1])+'/'+str(episode_date[2])) 
			try:
				if title in self.lastUpdated:
					if episode_date == self.lastUpdated[title]:
						self.howOld(episode_date)
						print 'No updates.'
						logging.info('No updates.')
						return(1)
				self.howOld(episode_date)
				self.lastUpdated[title] = episode_date
			except:
				print "Bad feed date."
				logging.warning('Bad feed date.')
				return(1)
		except:
			print 'Bad feed details.'
			logging.warning('Bad feed details.')
			return(1)
		return(0)
		
	def saveLastUpdated(self):
		'''Save the structure we have been creating to disk.'''
		try:
			f = open(LASTUPDATEDFILE, 'wb')
			pickle.dump(self.lastUpdated, f)
			f.close()
		except:
			print "Failed to write to lastupdated file."
			logging.warning("Failed to write to lastupdated file.")
			return(1)
		return(0)
	
	def readLastUpdated(self):
		'''Populate the lastUpdated dictionary from the file.'''
		try:
			f = open(LASTUPDATEDFILE, 'rb')
		except:
			print 'Could not open last updated file: '+LASTUPDATEDFILE
			logging.warning('Could not open last updated file: '+LASTUPDATEDFILE)
			self.lastUpdated = {}
			return(1)
		self.lastUpdated = pickle.load(f)
		return(0)
		
	def handleRedirect(self,link):
		if 'redirect' in link:
			if '99percent' in link:
				tweak = 'cdn'+link.split('cdn')[1]
			if 'wired' in link:
				tweak = link.split('redirect.mp3/')[1]				
			else:
				tweak = link.split('?')[1]
		else:
			tweak = link
		return(tweak)
		
	def getPod(self,urltuple):
		''' Open the feed list and then fetch the top items from that feed - complicated version. '''
		label,url,type = urltuple
		print label+'...\t',
		d = feedparser.parse(url)
		if self.checkHtmlStatus(d) != 0:
			return(1)
		try:
			for j,i in enumerate(d.entries):
				if j == 0:			# so far only get the first item from the feed.
					string = label + ": " + i.title
					print string
					logging.info(string)
					if type == 0:
						the_mp3 = i.link
					if type == 1:
						k=i['links']
						l=k[1]					# note that this is not 0!
						the_mp3=self.handleRedirect(l['href'])
					if type == 2:
						k=i['links']
						l=k[0]		
						the_mp3=self.handleRedirect(l['href'])
					logging.info('mp3 link:'+the_mp3)
					p = subprocess.call(["wget", "-q", "-nc", "-P", DESTINATIONDIR, the_mp3])
		except:
			print 'Failed to process file.'
			logging.warning('Failed to process file.')
			return(1)
		self.downloadCount += 1
		return(0)

	def processRssList(self,verbose):
		'''Get each rss url and call the routine to fetch the pods from each one. '''
		self.readLastUpdated()
		if verbose == 0:
			for k in self.podlist:
				if self.getPod(k) == 0:
					self.saveLastUpdated()
		else:
			for k in self.testlist:
				if self.getPod(k) == 0:
					self.saveLastUpdated()
		print "Number of downloads: "+str(self.downloadCount)
		logging.info("Number of downloads: "+str(self.downloadCount))
		print "Starting db initialise..."
		p = subprocess.check_output(["mpc", "update"])	# reinitialise the db

if __name__ == "__main__":
	''' Typically run this as a standalone prog to collect the podcasts asynchronously from the playing. '''
	parser = argparse.ArgumentParser( description='podfetch - get podcasts from the web. \
	Use -v option when debugging.' )
	parser.add_argument("-v", "--verbose", help="increase output - lots more logged in ./log/podfetch.log",
                    action="store_true")
	args = parser.parse_args()
	if args.verbose:
		verbose = 1
		logging.basicConfig(	filename=LOGFILE,
								filemode='w',
								level=logging.DEBUG )
	else:
		verbose = 0
		logging.basicConfig(	filename=LOGFILE,
								filemode='w',
								level=logging.INFO )
	
#	Default level is warning, level=logging.INFO log lots, level=logging.DEBUG log everything
	logging.warning(datetime.datetime.now().strftime('%d %b %H:%M')+". Running podfetch class as a standalone app")
	myPodfetch = podfetch()
	print '>>> podfetch <<<'
	print 'Destination directory: ',DESTINATIONDIR
	print 'Stored latest dates in: ',LASTUPDATEDFILE
	myPodfetch.processRssList(verbose)


	
