# Built-in
import sys, os, time, re, json, html, base64, shutil, subprocess, datetime
import clipboard
import pyperclip
from string import Template
from datetime import timedelta

# Global
from selenium import webdriver
from selenium.webdriver.chrome.options import Options 
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import ElementNotInteractableException
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import WebDriverException

import requests
from requests.exceptions import ConnectionError
import urllib.request as request

from io import BytesIO
import win32clipboard
from PIL import Image

import speech_recognition as sr
# Local
from boot.pyrebase import database
from boot.firebase_admin import firestore



class WhatsAppBot:
  def __init__(self):
    self.on = True
    self.driver = None
    self.dir = os.path.dirname(__file__)
    self.dir_downloads = os.path.dirname(self.dir + '\\downloads\\')
    self.dir_uploads = os.path.dirname(self.dir + '\\uploads\\')

    # Authentication
    self.authenticated = False
    self.streaming = False
    self.authentication_hash = ''

    # Chat
    self.phone_number = '' # Put your phone number here
    self.chat_opened = False
    self.chat_message_text = ''
    self.chat_message_sent = False
    self.chats_with_unread_messages = None
    self.count_of_chats_with_unread_messages = None
    self.chat_last_session = None
    ## Flow
    self.flow_enabled_key = None
    self.flow_enabled_data = None
    ## Message
    self.last_message = { 'contact_phone': 'message_id' }

    # Command
    self.executing_command = False
    self.bypass_stream_executing = False
    self.commands = { '@': False, 'action': 'action_name', 'payload': { 'variable': 'value' } }

    # Contact
    self.contact_name_in_chat = ''
    self.selected_contact_name = None

    # Setting
    self.settings = { '@': { 'autoresponder': True, 'log': { '@': True, 'terminal': True }, 'restart': False } }
    ## Chat
    ### Flow
    self.settings_chat_flow = { 'execution': { '@': False } }
    ## Command
    ### Execute
    self.settings_command_execute = { '@': True, 'close_chat_after_execute': True, 'remove_after_execute': False, 'remove_inactived_message': False }


  def boot(self):
    self.log('\x1b[0;30;43m' + 'WhatsAppBot booting...' + '\x1b[0m' + '.')

    # Database
    try:
      #* Commands
      database.child('commands').child(self.phone_number).child('@').set(self.commands)
      #* Flow
      database.child('chats').child('flows').child(self.phone_number).stream(self.flowing)
      #* Settings
      database.child('settings').set(self.settings)
      #database.child('settings').child(self.phone_number).set(self.settings)
      #*? Chats
      database.child('settings').child('chat').child('flow').set(self.settings_chat_flow)
      #*? Commands
      database.child('settings').child('command').child('execution').set(self.settings_command_execute)
      #* Stream
      #*? Settings
      database.child('settings').stream(self.setting)
      #database.child('settings').child(self.phone_number).stream(self.setting)
      #*? Commands
      database.child('commands').child(self.phone_number).stream(self.executing)
    except:
      self.log('\x1b[6;30;41m' + 'WhatsAppBot booting... failed! [1] Connecting again...' + '\x1b[0m')
      time.sleep(1)
      return self.boot()

    try:
      # Driver
      #* Boot
      ### Chrome
      chromeOptions = webdriver.ChromeOptions()
      chromeOptions.add_experimental_option('prefs', {
        'download.default_directory': self.dir_downloads,
        'safebrowsing.enabled': 'false'
      })
      #options.add_argument('lang=pt-br')
      chromeOptions.add_argument('--lang=en-us')
      chromeOptions.add_argument('log-level=3')
      #* Instance
      ### Chrome
      self.driver = webdriver.Chrome(executable_path=r'chromedriver.exe', options=chromeOptions)
      ### Firefox
      #self.driver = webdriver.Firefox()
      #* Configure
      self.driver.maximize_window()
      #self.driver.implicitly_wait(1) #default is 0
      self.driver.set_page_load_timeout(10)
      #* Get
      self.driver.get('https://web.whatsapp.com/')
    except TimeoutException:
      self.log('\x1b[6;30;41m' + 'WhatsAppBot booting... failed! [2] Refreshing page...' + '\x1b[0m')
      self.driver.refresh()
    #except:
    #  self.log('\x1b[6;30;41m' + 'WhatsAppBot booting... failed! [3] Trying again in 10 seconds...' + '\x1b[0m')
    #  time.sleep(10)
    #  return self.boot()

    #self.driver.execute_script(
    '''
    setInterval(function(){
      var videos = document.getElementsByTagName("video");
      if (videos.length != 0) {
        videos[0].removeAttribute("autoplay")
      }
    }, 10);
    '''
    #)

    self.log('\x1b[6;30;42m' + 'WhatsAppBot started!' + '\x1b[0m' + '.')
  def log(self, message, color = None, now = True):
    if not self.settings['@']['log']['@']:
      return
    if not self.settings['@']['log']['terminal']:
      return

    if now:
      now = datetime.datetime.now().time()
      print(f'[{now}] ', message)
    else:
      print(message)
  def shutdown(self):
    self.on = False
    self.driver.quit()
    self.driver = None

  def get_last_downloaded_file_name(self, timeout = 10): # timeout in seconds
    main_window = self.driver.current_window_handle

    # Open new window
    self.driver.execute_script("window.open()")
    # Switch to new tab
    self.driver.switch_to.window(self.driver.window_handles[-1])
    # Navigate to chrome downloads
    self.driver.get('chrome://downloads')
    # Set file name
    file_name = None
    # Get file name
    while True:
      try:
        downloadPercentage = self.driver.execute_script("""
        var progress = document.querySelector('downloads-manager').shadowRoot.querySelector('#downloadsList downloads-item').shadowRoot.querySelector('#progress')
        if (progress !== null) {
          return progress.value;
        }
        else {
          return false;
        }
        """)

        if downloadPercentage == False or downloadPercentage == 100:
          file_name = self.driver.execute_script("return document.querySelector('downloads-manager').shadowRoot.querySelector('#downloadsList downloads-item').shadowRoot.querySelector('div#content  #file-link').text")
          break
      except:
        pass

      time.sleep(1)

      if time.time() > time.time() + timeout:
        break
    # Close current tab
    self.driver.execute_script("window.close()")

    self.driver.switch_to.window(main_window)

    return file_name

  #! Authentication
  # Authenticate
  def authenticate(self):
    if not self.driver: return

    if not self.authenticated:
      try:
        # Click to reload QR Code button
        qr_refresh_element = self.driver.find_element_by_xpath('//button[(@role="button" or @class="_2znac") and contains(@style, "scale")]')

        self.log('\x1b[0;30;43m' + 'Refreshing QR Code...' + '\x1b[0m')

        self.wait(1)

        qr_refresh_element.click()

        self.wait(1)

        self.log('\x1b[6;30;42m' + 'Refreshing QR Code... done!' + '\x1b[0m')
      except NoSuchElementException:
        pass
      except ElementNotInteractableException:
        self.log('\x1b[6;30;41m' + 'Refreshing QR Code... failed! (Element not iterable)!' + '\x1b[0m')
        return
      except:
        self.log('\x1b[6;30;41m' + 'Refreshing QR Code... failed! (Unknown error)!' + '\x1b[0m')
        return

    try:
      qr_string = self.driver.find_element_by_xpath('//div[@data-ref]').get_attribute('data-ref')

      if qr_string != self.authentication_hash:
        self.authentication_hash = qr_string

        self.authenticated = False

        database.child('authentications').child(self.phone_number).set({ "hash": self.authentication_hash, "@": False })

        self.log('\x1b[0;31;40m' + f"Authentication Hash: {qr_string}" + '\x1b[0m')
    except NoSuchElementException:
      try:
        self.driver.find_element_by_xpath('//div[contains(@class, "copyable-text selectable-text")]')
        self.wait(1)
        self.login()
      except NoSuchElementException:
        #self.log('\x1b[6;30;41m' + 'Auth error! (No Such Element)' + '\x1b[0m')
        self.authenticated = False
      #except:
      #  self.log('\x1b[6;30;41m' + 'Auth error! (Unknown error)!' + '\x1b[0m')
      #  self.authenticated = False
    except:
      self.authenticated = False
  # Login
  def login(self):
    if not self.driver: return

    if not self.authenticated:
      self.authenticated = True

      database.child('authentications').child(self.phone_number).update({ "@": True })

      self.log('\x1b[6;30;42m' + 'WhatsAppBot authenticated!' + '\x1b[0m' + '.')

      executed = 0
      if self.commands is not None:
        for key, command in self.commands.items():
          if self.execute(key, command):
            executed += 1

      if executed > 0:
        self.log('\x1b[0;37;44m' + 'Commands executed:' + '\x1b[0m' + f' {executed}')
  # Logout
  def logout(self):
    if not self.driver: return

    #self.driver.delete_all_cookies()
    self.authenticated = False

  #! Contact
  ## Select contact
  def select_contact(self, by, source, contact = None, index = 0):
    self.log('\x1b[0;30;44m' + 'Selecting contact...' + '\x1b[0m')

    if by == 'name':
      if source == 'in_chat_list':
        self.select_contact_by_name_loaded_in_chat_list(contact, index)
      elif source == 'in_chat_list_search':
        self.select_contact_by_name_in_chat_list_search(contact, index)
      elif source == 'in_chat_list_pinned':
        pass
      elif source == 'in_chat_list_not_in_pinned':
        pass
      elif source == 'in_new_search':
        pass
      elif source == 'in_group_list':
        pass
    elif by == 'phone':
      if source == 'in_chat_list_search':
        pass
      elif source == 'in_new_search':
        pass
      elif source == 'in_group_list':
        pass
    elif by == 'index':
      if source == 'in_new':
        pass
      elif source == 'in_chat_list':
        pass
      elif source == 'in_chat_list_pinned':
        pass
      elif source == 'in_chat_list_not_in_pinned':
        pass      

    self.log('\x1b[6;30;42m' + 'Contact selected!' + '\x1b[0m')
    self.log('\x1b[6;30;42m' + f"Contact selected by: {by}" + '\x1b[0m')
    self.log('\x1b[6;30;42m' + f"Contact source: {source}" + '\x1b[0m')
  ### By name
  def select_contact_by_name_in_chat_list_search(self, contact_name, index = 0):
    #try:
    #  self.driver.find_element_by_xpath(f'//div[@role="option" and @aria-selected="true" and .//span[@dir="auto" and @title="{contact_name}"]]')
    #  return
    #except:
    #  pass

    try:
      if not self.selected_contact_name or not self.chat_opened:
        chat_list_search_element = WebDriverWait(self.driver, 1).until(
          EC.presence_of_element_located(
            (By.XPATH, '//div[@id="app"]//div[contains(@class, "copyable-text selectable-text")]')
          )
        )
        chat_list_search_element.click()
        chat_list_search_element.send_keys(contact_name)
        chat_list_search_element.send_keys(Keys.ENTER)

        self.chat_opened = True

        self.selected_contact_name = contact_name
    except NoSuchElementException:
      self.selected_contact_name = None
      self.chat_opened = False
    except ElementNotInteractableException:
      self.selected_contact_name = None
      self.chat_opened = False
    except StaleElementReferenceException:
      self.selected_contact_name = None
      self.chat_opened = False
    #except:
    #  self.chat_opened = False
  def select_contact_by_name_loaded_in_chat_list(self, contact_name, index = 0):
    try:
      # TODO refactor with webdriver wait
      chat_item = self.driver.find_element_by_xpath(f'//span[@title="{contact_name}"]')
      chat_item.click()
      self.chat_opened = True
    except NoSuchElementException:
      self.chat_opened = False
    #except:
    #  pass
  def open_contact_info(self):
    try:
      header_contact_image = self.driver.find_element_by_xpath('//header[@class="_1UuMR"]/div[@class="_1vGIp"]')
      header_contact_image.click()
      return True
    except:
      return False
  def get_contact_info(self):
    contact = {}

    try:
      if self.chat_opened:
        if self.open_contact_info():
          contact_info = WebDriverWait(self.driver, 1).until(
            EC.presence_of_element_located(
              (By.XPATH, '//div[@class="i5ly3 _299go"]')
            )
          )

          contact_id = contact_info.find_element_by_xpath('.//span[contains(@class, "copyable-text")]/span[@class="_3Tk1z _27rts"]')
          try:
            contact_name = contact_info.find_element_by_xpath('(.//span[@class="OXGxe _1VzZY"]|.//span[@class="_3ZYWe _27rts"]/span)[last()]')
          except:
            contact_name = None
          try:
            contact_image = contact_info.find_element_by_xpath('.//div[@class="Lffaz"]//img')
          except:
            contact_image = None

          if contact_id:
            contact['id'] = contact_id.get_attribute('innerHTML')[1:].replace(' ', '').replace('-', '')

          # TODO if contact['name'] == contact['id'] then contact['name'] = None
          if contact_name:
            try:
              emojis_imgs = contact_name.find_elements_by_xpath('.//img[@data-plain-text]')
              for emoji_img in emojis_imgs:
                emoji = emoji_img.get_attribute('data-plain-text')
                self.driver.execute_script("arguments[0].innerHTML = arguments[1];", emoji_img, emoji)
            except:
              pass

            contact['name'] = contact_name.get_attribute("textContent")
          else:
            contact['name'] = None

          if contact_image:
            matches = re.search(r'u=(.*)%40c', contact_image.get_attribute('src'))
            if matches:
              contact['image'] = matches.group(1)
    except TimeoutException:
      # TODO emit error
      pass

    return contact

  #! Chat
  def open_chat(self, element):
    try:
      element.click()
      self.chat_opened = True
      return True
    except:
      self.chat_opened = False
      return False
  def close_chat(self):
    first_chat = self.driver.find_element_by_xpath('//div[@id="app"]//div[contains(@aria-label, "Chat list")]/*[1]')
    first_chat.click()

    self.chat_opened = False
    self.selected_contact_name = None
  def check_unread_chats_by_title(self):
    matches = re.search(r'\((.*)\)', self.driver.title)

    if matches:
      try:
        count = int(matches.group(1))
        self.count_of_chats_with_unread_messages = count
        return True
      except:
        self.chats_with_unread_messages = []
        return False
    else:
      self.chats_with_unread_messages = []
      return False
  def check_unread_chats_in_chat_list(self):
    chats_with_unread_messages = self.driver.find_elements_by_xpath('//div[@id="pane-side"]//div[@role="option" and not(.//span[contains(@data-icon, "status-")]) and .//span[@class="VOr2j"] and @aria-selected="false"]')

    if chats_with_unread_messages:
      self.chats_with_unread_messages = chats_with_unread_messages
      self.count_of_chats_with_unread_messages = len(self.chats_with_unread_messages)
      return True
    else:
      self.chats_with_unread_messages = []
      self.count_of_chats_with_unread_messages = 0
      return False
  def check_and_return_unread_chats_in_chat_list(self):
    chats_with_unread_messages = self.driver.find_elements_by_xpath('//div[@id="pane-side"]//div[@role="option" and not(.//span[@data-icon="status-dblcheck"] or .//span[@data-icon="status-time"] or .//span[@data-icon="muted"]) and .//span[@class="VOr2j"] and @aria-selected="false"]')
    if chats_with_unread_messages:
      return chats_with_unread_messages
    else:
      return []
  def get_chat_item_info(self, chat_list_item):
    #! Contact
    #try:
    #  chat_contact_image_src = chat_list_item.find_element_by_xpath('.//img').get_attribute('src')

    #  matches = re.search(r'u=(.*)%40c', chat_contact_image_src)
    #  if matches:
    #    chat_contact_id = matches.group(1)

    #  chat_contact_name = chat_list_item.find_element_by_xpath('.//span[@dir="auto" and @title]').get_attribute("textContent")

    #  if chat_contact_name[1:] == '+' and chat_contact_name[1:].replace(' ', '').replace('-', '') == chat_contact_id:
    #    chat_contact_name = None
    #except NoSuchElementException:
    #  chat_contact_image_src = None
    #  chat_contact_id = None
    #  chat_contact_name = None

    #! Message
    #? Count
    try:
      chat_message_count = int(chat_list_item.find_element_by_xpath('.//span[@aria-label]').get_attribute("textContent"))
    except:
      chat_message_count = 0
    #? Type
    chat_message_type_audio = False
    chat_message_type_ptt = False
    chat_message_type_document = False
    chat_message_type_image = False
    chat_message_type_video = False
    chat_message_type_location = False
    chat_message_type_contact = False

    try:
      chat_list_item.find_element_by_xpath('.//span[@class="_3MjzD"]/div[contains(@class, "_3sDwr") or contains(@class, "status-")]')
      chat_message_type_text = False
    except NoSuchElementException:
      chat_message_type_text = True

    chat_message_text = ''
    if not chat_message_type_text:
      ### Audio
      try:
        chat_message_type_audio = chat_list_item.find_element_by_xpath('.//span[@data-icon="status-audio"]')
      except NoSuchElementException:
        chat_message_type_audio = False
      ### PTT
      try:
        chat_message_type_ptt = chat_list_item.find_element_by_xpath('.//span[@data-icon="status-ptt"]')
      except NoSuchElementException:
        chat_message_type_ptt = False
      ### Document
      try:
        chat_message_type_document = chat_list_item.find_element_by_xpath('.//span[@data-icon="status-document"]')
      except NoSuchElementException:
        chat_message_type_document = False
      ### Image
      try:
        chat_message_type_image = chat_list_item.find_element_by_xpath('.//span[@data-icon="status-image"]')
      except NoSuchElementException:
        chat_message_type_image = False
      ### Video
      try:
        chat_message_type_video = chat_list_item.find_element_by_xpath('.//span[@data-icon="status-video"]')
      except NoSuchElementException:
        chat_message_type_video = False
      ### Location
      try:
        chat_message_type_location = chat_list_item.find_element_by_xpath('.//span[@data-icon="status-location"]')
      except NoSuchElementException:
        chat_message_type_location = False
      ### Contact
      try:
        chat_message_type_contact = chat_list_item.find_element_by_xpath('.//span[@data-icon="status-vcard"]')
      except NoSuchElementException:
        chat_message_type_contact = False
    else:
      try:
        chat_message_text = chat_list_item.find_element_by_xpath('.//span[@class="_3MjzD"]').get_attribute('title')[1:-1]
      except NoSuchElementException:
        chat_message_text = ''

    if chat_message_type_text:
      chat_message_type = 'text'
    elif chat_message_type_ptt:
      chat_message_type = 'ptt'
    elif chat_message_type_audio:
      chat_message_type = 'audio'
    elif chat_message_type_document:
      chat_message_type = 'document'
    elif chat_message_type_image:
      chat_message_type = 'image'
    elif chat_message_type_video:
      chat_message_type = 'video'
    elif chat_message_type_location:
      chat_message_type = 'location'
    elif chat_message_type_contact:
      chat_message_type = 'contact'
    else:
      chat_message_type = None

    chat_item_info = {
      "@": chat_list_item,
      #"contact": {
      #  "id": chat_contact_id,
      #  "name": chat_contact_name,
      #  "image": chat_contact_image_src,
      #},
      "message": {
        "@": {
          "@type": chat_message_type,
          "text": chat_message_text
        },
        "unreads": chat_message_count
      }
    }

    return chat_item_info
  def select_chats_with_unread_messages(self, limit = None):
    try:
      chats_unread = WebDriverWait(self.driver, 3).until(
        EC.presence_of_all_elements_located(
          (By.XPATH, '//div[@id="app"]//span[@class="VOr2j"]')
        )
      )

      i = 0
      for chat_unread in chats_unread:
        i += 1
        #unread_attribute = chat_unread.get_attribute('aria-label')
        #unread_count = int(unread_attribute.split(" ", 1)[0])

        chat_unread.click()
        self.chat_opened = True
        time.sleep(1)

        if limit and limit == i:
          break
    except TimeoutException:
      pass
  #? Input chat
  ## Text
  def click_to_input_chat_text(self):
    try:
      #chat_input_text_element = self.driver.find_element_by_xpath('//div[@id="app"]//div[contains(@class, "copyable-text selectable-text") and @spellcheck]')
      chat_input_text_element = WebDriverWait(self.driver, 2).until(
        EC.presence_of_element_located(
          (By.XPATH, '//div[@id="app"]//div[contains(@class, "copyable-text selectable-text") and @spellcheck]')
        )
      )
      chat_input_text_element.click()

      return chat_input_text_element
    except:
      return False
  def click_to_input_chat_caption(self):
    try:
      chat_input_caption_element = WebDriverWait(self.driver, 10).until(
        EC.presence_of_element_located(
          (By.XPATH, '//div[contains(@class, "copyable-text selectable-text") and @spellcheck and not(../div[contains(text(), "message")])]')
        )
      )
      chat_input_caption_element.click()
      return chat_input_caption_element
    except ElementNotInteractableException:
      return False
    except:
      return False
  ## Attach
  def click_to_input_chat_attach(self):
    try:
      WebDriverWait(self.driver, 2).until(EC.presence_of_element_located((By.XPATH, '//div[@role="button" and @title="Attach"]'))).click()
      return True
    except:
      return False
  def input_chat_attach(self, path):
    try:
      input_chat_attach = WebDriverWait(self.driver, 2).until(
        EC.presence_of_element_located(
          (By.XPATH, '//div[@id="app"]//input[@accept="*"]')
        )
      )
      input_chat_attach.send_keys(path)
      return True
    except:
      self.log('\x1b[6;30;41m' + 'Input file failed! [Unknown error]' + '\x1b[0m')
      return False
  ### Audio
  def input_chat_attach_audio(self, path):
    try:
      input_chat_attach = WebDriverWait(self.driver, 2).until(
        EC.presence_of_element_located(
          (By.XPATH, '//div[@id="app"]//input[@accept="*"]')
        )
      )
      input_chat_attach.send_keys(path)
      return True
    except:
      self.log('\x1b[6;30;41m' + 'Input file audio failed! [Unknown error]' + '\x1b[0m')
      return False
  ### Document
  def input_chat_attach_document(self, path):
    try:
      input_chat_attach = WebDriverWait(self.driver, 2).until(
        EC.presence_of_element_located(
          (By.XPATH, '//div[@id="app"]//input[@accept="*"]')
        )
      )
      input_chat_attach.send_keys(path)
      return True
    except:
      self.log('\x1b[6;30;41m' + 'Input file document failed! [Unknown error]' + '\x1b[0m')
      return False
  ### Image
  def input_chat_attach_image(self, path):
    try:
      input_chat_attach_image_video = WebDriverWait(self.driver, 2).until(
        EC.presence_of_element_located(
          (By.XPATH, '//div[@id="app"]//input[@accept="image/*,video/mp4,video/3gpp,video/quicktime"]')
        )
      )
      input_chat_attach_image_video.send_keys(path)
      return True
    except:
      self.log('\x1b[6;30;41m' + 'Input file image failed! [Unknown error]' + '\x1b[0m')
      return False
  ### Video
  def input_chat_attach_video(self, path):
    try:
      input_chat_attach_image_video = WebDriverWait(self.driver, 10).until(
        EC.presence_of_element_located(
          (By.XPATH, '//div[@id="app"]//input[@accept="image/*,video/mp4,video/3gpp,video/quicktime"]')
        )
      )
      input_chat_attach_image_video.send_keys(path)
      return True
    except TimeoutException:
      self.log('\x1b[6;30;41m' + 'Input file video failed! [Timeout]' + '\x1b[0m')
      return False
    except:
      self.log('\x1b[6;30;41m' + 'Input file video failed! [Unknown error]' + '\x1b[0m')
      return False
  #! Chat -> Flow
  def execute_chat_flow(self, contact, message):
    #try:
      flows = self.flow_enabled_data
      if not flows:
        return

      session = self.start_chat_session(contact["id"])
      keys_stored = session["@"] # '1;2+3+'
      flow_level = session["@level"] # 1

      keys_found = ''
      keys_actived = ''

      start_at = None

      restart = True
      while restart:
        restart = False

        if keys_stored:
          started = True # True
        else:
          started = False

        for key, flow in flows.items(): # TODO replace to key, value?
          if key == 'children':
            children = flow # children = value
            print(children)

          if start_at and key != start_at:
            continue
          if key[-1:] not in [';', '+']:
            continue

          if not started:
            keys_stored = keys_found
          else:
            keys_stored = keys_stored #[4] '1;2+3+'

          keys_found += key #[4] 1;2+3+

          # Get flow?
          if keys_stored and keys_stored == keys_found: #[2] '1;2+3+' == 1;2+3+
            keys_actived = keys_found

            if key[-1:] == ';': # Not iterable
              break
            elif key[-1:] == '+': # Iterable
              if 'settings' in flow:
                flow_settings = flow['settings']
              else:
                flow_settings = None
              # TODO self.get_chat_flow_settings(flow, 'convert_ptt_to_text_option')?

              if flow["@"] == 'menu':
                #? Select menu option
                if 'option' not in session:
                  #try:
                  if not message["text"] or type(message["text"]) != str:
                    if flow_settings and flow_settings.get('convert_ptt_to_text_option', None) and message['@type'] == 'ptt':
                      response = self.read_and_save_last_message_in_chat('ptt')

                      ptt_full_path = response['messages'][0]['ptt']
                      ptt_dir_path = os.path.dirname(ptt_full_path)
                      ptt_file_path = os.path.basename(ptt_full_path)

                      ptt_output_file_path = os.path.join(ptt_dir_path, ptt_file_path.replace('.oga', '.wav'))

                      converted = self.convert_media_file_using_ffmpeg(ptt_full_path, ptt_output_file_path)
                      if converted:
                        text_in_ptt = self.read_text_from_ptt(ptt_output_file_path)
                        if text_in_ptt:
                          message["text"] = text_in_ptt
                          self.log('\x1b[6;30;42m' + 'Option text recognized in PTT:' + '\x1b[0m' + f' {text_in_ptt}')
                    else:
                      self.log('\x1b[6;30;41m' + 'Non-text message used in flow menu options' + '\x1b[0m' + ':')
                      self.close_chat()
                      return
                  #except:
                  #  self.log('\x1b[6;30;41m' + 'Error in message used in flow menu options' + '\x1b[0m' + ':')
                  #  print(message)
                  #  self.close_chat()
                  #  return

                  # Non iterable as option
                  option = message["text"] + '-'
                  # Iterable as option
                  if option not in flow:
                    option = message["text"] + '+'
                  # Options id and references
                  if option not in flow:
                    for flow_option in flow["options"]:
                      # id
                      option_id = flow["options"][flow_option]["id"]
                      if message["text"] == option_id:
                        option = flow_option
                        break
                      # references
                      references = flow["options"][flow_option]["references"].split(",")
                      for reference in references:
                        if message["text"].lower() == reference:
                          option = flow["options"][flow_option]["@"]
                          break
                      if option in flow:
                        break
                  # Recall
                  if option not in flow:
                    if 'recall' in flow:
                      recalls = flow['recall']['references'].split(",")
                      for recall in recalls:
                        if message['text'].lower() == recall:
                          self.execute_component_flow(contact, message, flow)
                          return self.close_chat()
                else:
                  option = session['option']
                  # Deselect option
                  if flow_settings and 'words_to_deselect_option' in flow_settings:
                    deselects = flow_settings['words_to_deselect_option'].split(",")
                    for deselect in deselects:
                      if message['text'].lower() == deselect:
                        self.execute_component_flow(contact, message, flow)
                        self.set_chat_session(contact["id"], {
                          "@": keys_found,
                          "@component": flow["@"],
                          "@level": flow_level
                        })
                        return self.close_chat()

                #? Enter menu option
                if option in flow:
                  flows1 = flow[option]
                  #flow = flow1

                  if flows1['@'] == 'node':
                    pass
                  elif flows1["@"] == 'menu':
                    response = self.execute_component_flow(contact, message, flows1)
                    if response:
                      self.set_chat_session(contact["id"], {
                        "@": keys_found + option,
                        "@component": "menu",
                        "@level": flow_level + 1
                      })
                    break
                  elif flows1["@"] == 'link':
                    # TODO remove flow_level?
                    self.set_chat_session(contact["id"], {
                      "@": flows1["from"],
                      "@component": "link",
                      "@level": flows1["flow_level"]
                    })
                    # Set flow loop variables
                    # TODO build keys_stored dinamically
                    keys_stored = ''
                    keys_found = flows1["from"]
                    start_at = flows1["to"]
                    flow_level = flows1["flow_level"]
                    # Restart flow loop and break current loop
                    flows = self.flow_enabled_data
                    restart = True
                    break
                  elif flows1["@"] == 'send_attachment':
                    # TODO check if component was executed with successfully
                    # Execute component flow
                    self.execute_component_flow(contact, message, flows1)
                    # Send Menu again
                    # TODO send menu message again as schedule message after checking if attachment was sent
                    #self.execute_component_flow(contact, message, flow)
                    # Close Chat
                    return self.close_chat()
                  elif flows1["@"] == 'receive_attachment':
                    if 'option' in session:
                      if message['@type'] in flows1['types'] or not flows1['types']:
                        self.execute_component_flow(contact, message, flows1)
                      else:
                        self.send_message_text(flows1['messages']['notice']['type'])
                    else:
                      # Send CTA message
                      self.send_message_text(flows1['messages']['info']['cta'])
                      # TODO create update session?
                      # Set session
                      self.set_chat_session(contact['id'], {
                        "@": keys_found,
                        "@component": "menu",
                        "@level": flow_level,
                        'option': option
                      })
                    # Close Chat
                    return self.close_chat()
                  elif flows1["@"] == 'finish_session':
                    self.reset_chat_session(contact["id"])
                    self.execute_component_flow(contact, message, flows1)
                    self.close_chat()
                    return
                else:
                  # Invalid option
                  if flow_settings and 'respond_if_option_is_invalid' in flow_settings:
                    if flow_settings['respond_if_option_is_invalid']:
                      self.send_message_text('Opção inválida!')
                  else:
                    self.send_message_text('Opção inválida!')

                  return self.close_chat()
              elif flow['@'] == 'node':
                pass
          elif keys_stored and keys_stored.startswith(keys_found): #[2] '1;2+3+' starts with 1;2+1+
            keys_actived = keys_found

            if key[-1:] == ';': #[1] 1;
              continue
            elif key[-1:] == '+': #[2] 2+
              flows = flow
              restart = True
              break
          elif started:
            if key[-1:] == '+': #[3] 1+
              keys_found = keys_actived #[3] '1;2+3+' = 1;2+
              continue

          # Execute component flow
          response = self.execute_component_flow(contact, message, flow)

          if response == -1:
            break

          # Update keys_stored with metadata of current node flow
          if response:
            self.set_chat_session(contact["id"], {
              "@": keys_found,
              "@component": flow["@"],
              "@level": flow_level
            })

      self.close_chat()
  def render_component_message(self, message, contact):
    if '$' in message:
      template = Template(message)

      if '$contact_name' in message:
        message = template.substitute(contact_name = contact['name'] if contact['name'] else '')
    return message
  def execute_component_flow(self, contact, message, flow):
    #? Render component message
    if 'message' in flow:
      component_message = flow["message"]
      if '$' in component_message:
        template = Template(component_message)
        if '$contact_name' in component_message:
          component_message = template.substitute(contact_name = contact['name'] if contact['name'] else '')

    #? Execute component flow
    if flow["@"] == 'start_session':
      if 'triggers' in flow:
        triggered = False
        triggers = flow["triggers"].split(",")
        for trigger in triggers:
          if message["text"] and message["text"].lower() == trigger:
            triggered = True
            break
        if not triggered:
          return -1
      return self.send_message_text(component_message)
    elif flow["@"] == 'menu':
      for flow_option in flow["options"]:
        component_message += "\n" + str(flow["options"][flow_option]["id"]) + " - " + flow["options"][flow_option]["label"]
      if 'recall' in flow:
        component_message += '\n\n' + flow['recall']['message']
      return self.send_message_text(component_message)
    elif flow["@"] == 'send_attachment':
      return self.execute(None, flow["command"])
    elif flow['@'] == 'receive_attachment':
      response = self.read_and_save_last_message_in_chat(message['@type'])

      if flow['~convert']:
        if flow['~convert']['@'] == 'text' and (message['@type'] == 'ptt' or message['@type'] == 'audio'):
          audio_type = response['messages'][0]['@']
          audio_full_path = response['messages'][0][audio_type]
          data_converted = self.convert_audio_to_text(audio_full_path)

      if flow['~reply']:
        if flow['~reply']['@'] == '$messages':
          # TODO refactor check if attachment was read
          if not response['messages']:
            return self.send_message_text(flow['messages']['error']['received'])
          # TODO refactor check if attachment was saved
          if not response['messages'][0][message['@type']]:
            return self.send_message_text(flow['messages']['error']['saved'])
          success_default = flow['messages']['success']['@default']
          return self.send_message_text(flow['messages']['success'][success_default])
        elif flow['~reply']['@'] == '$~converted':
          message_id = response['messages'][0]['@meta']['message_id']
          message_text = ''
          if 'header' in flow['~reply']:
            message_text += flow['~reply']['header']
          message_text += data_converted
          return self.send_message_text_replying(message_text, message_id)

      return False
    elif flow["@"] == 'finish_session': # TODO rename to reset_session?
      return self.send_message_text(component_message)
    else:
      return False
  def get_chat_flow(self):
    pass
  #! Chat -> Message
  #? Read message
  def read_received_message_in_chat(self, order = -1):
    #* //span[@aria-live and contains(text(), "unread")]

    #* //div[@id="app"]//div[contains(@aria-label, "Message list")]/div[contains(@data-id, "false")]
    #* //div[@id="app"]//div[contains(@aria-label, "Message list")]/div[contains(@class, "message-in")

    try:
      if order == 1:
        message_in = self.driver.find_element_by_xpath('//div[@id="app"]//div[@role="region" and contains(@aria-label, "Message list")]/div[contains(@class, "message-in")]')
      elif order == -1:
        message_in = self.driver.find_element_by_xpath('(//div[@id="app"]//div[@role="region" and contains(@aria-label, "Message list")]/div[contains(@class, "message-in")])[last()]')

      self.log(message_in.get_attribute('innerHTML'))
    except:
      pass
  def read_received_messages_text_in_chat(self, order = -1, limit = 1):
    #* //span[@aria-live and contains(text(), "unread")]

    #* //div[@id="app"]//div[@class="tSmQ1" or contains(@aria-label, "Message list")]/div[contains(@data-id, "false")]
    #* //div[@id="app"]//div[@class="tSmQ1" or contains(@aria-label, "Message list")]/div[contains(@class, "message-in")

    try:
      if order == -1 and limit == 1:
        incoming_chat_messages = self.driver.find_element_by_xpath('(//div[@id="app"]//div[@class="tSmQ1" and contains(@aria-label, "Message list")]/div[contains(@class, "message-in")])[last()]//span[contains(@class, "selectable-text")]/span')
        return incoming_chat_messages.get_attribute("textContent")
    except:
      pass
  def read_text_from_ptt(self, ptt_file, duration = 10):
    try:
      r = sr.Recognizer()
      ptt_file = sr.AudioFile(ptt_file)
      with ptt_file as source:
        audio = r.record(source, duration)
      return r.recognize_google(audio, language = 'pt-BR')
    except:
      return ''
  ## File content
  def get_file_content_chrome(self, uri):
    result = self.driver.execute_async_script("""
    var uri = arguments[0];
    var callback = arguments[1];
    var toBase64 = function(buffer){for(var r,n=new Uint8Array(buffer),t=n.length,a=new Uint8Array(4*Math.ceil(t/3)),i=new Uint8Array(64),o=0,c=0;64>c;++c)i[c]="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/".charCodeAt(c);for(c=0;t-t%3>c;c+=3,o+=4)r=n[c]<<16|n[c+1]<<8|n[c+2],a[o]=i[r>>18],a[o+1]=i[r>>12&63],a[o+2]=i[r>>6&63],a[o+3]=i[63&r];return t%3===1?(r=n[t-1],a[o]=i[r>>2],a[o+1]=i[r<<4&63],a[o+2]=61,a[o+3]=61):t%3===2&&(r=(n[t-2]<<8)+n[t-1],a[o]=i[r>>10],a[o+1]=i[r>>4&63],a[o+2]=i[r<<2&63],a[o+3]=61),new TextDecoder("ascii").decode(a)};
    var xhr = new XMLHttpRequest();
    xhr.responseType = 'arraybuffer';
    xhr.onload = function(){ callback(toBase64(xhr.response)) };
    xhr.onerror = function(){ callback(xhr.status) };
    xhr.open('GET', uri);
    xhr.send();
      """, uri)

    if type(result) == int:
      raise Exception("Request failed with status %s" % result)

    return base64.b64decode(result)
  #? Convert message
  def convert_media_file_using_ffmpeg(self, source_file_path, destination_file_path):
    process = subprocess.run(['powershell.exe', 'ffmpeg', '-y', '-i', source_file_path, destination_file_path], stdout = subprocess.DEVNULL, stderr = subprocess.DEVNULL)

    if process.returncode != 0:
      return False
    else:
      return True
  def convert_audio_to_text(self, audio_full_path):
    audio_dir_path = os.path.dirname(audio_full_path)
    audio_file_path = os.path.basename(audio_full_path)

    output_file_path = os.path.join(audio_dir_path, audio_file_path.replace('.oga', '.wav'))

    converted = self.convert_media_file_using_ffmpeg(audio_full_path, output_file_path)
    if converted:
      text_in_ptt = self.read_text_from_ptt(output_file_path)
    else:
      text_in_ptt = ''

    return text_in_ptt
  #? Save message
  def create_to_save_dir(self, contact_id):
    to_save_dir = os.path.join(self.dir_downloads, contact_id)

    if not os.path.exists(to_save_dir):
      os.makedirs(to_save_dir)
  def save_file_to_downloads(self, content, relative_path):
    try:
      to_save_full_path = os.path.join(self.dir_downloads, relative_path)

      with open(to_save_full_path, 'wb') as downloaded_file:
        downloaded_file.write(content)
        downloaded_file.close()

      return to_save_full_path
    except:
      return False
  #? Read and save message
  def read_and_save_last_message_in_chat(self, type):
    #* //span[@aria-live and contains(text(), "unread")]
    #* //span[@aria-live and contains(text(), "unread")]/following-sibling::div[contains(@class, "message-in")]
    #* //div[@id="app"]//div[@class="tSmQ1" or contains(@aria-label, "Message list")]/div[./span[@aria-live and contains(text(), "unread")]]/following-sibling::div[contains(@class, "message-in")]
    #* Get unread messages-in
    #* //div[@id="app"]//div[@class="tSmQ1" or contains(@aria-label, "Message list")]/div[./span[@aria-live and contains(text(), "unread")]]/following-sibling::div[contains(@class, "message-in")]
    #* Get last message-in
    #* (//div[@id="app"]//div[@class="tSmQ1" or contains(@aria-label, "Message list")]//div[contains(@class, "message-in")])[last()]

    #* //div[@id="app"]//div[@class="tSmQ1" or contains(@aria-label, "Message list")]/div[contains(@data-id, "false")]
    #* //div[@id="app"]//div[@class="tSmQ1" or contains(@aria-label, "Message list")]/div[contains(@class, "message-in")]

    response = {
      #'contact': {
      #  'id': None
      #},
      'messages': []
    }

    try:
      message = WebDriverWait(self.driver, 1.5).until(
        EC.presence_of_element_located(
          (By.XPATH, '(//div[@id="app"]//div[@class="tSmQ1" or contains(@aria-label, "Message list")]//div[contains(@class, "message-in")])[last()]')
        )
      )

      if message:
        #! Get message meta
        data_id = message.get_attribute('data-id').replace('true_', '').replace('false_', '').replace('c.us_', '')
        contact_id, message_id = data_id.split('@', 1)
        meta = {
          'contact_id': contact_id,
          'message_id': message_id
        }

        #! Get message data
        message_text = None
        message_audio = None
        message_document = None
        message_image = None
        message_ptt = None
        message_video = None

        if type == 'text':
          message_text = None

          #* .//div[@class="copyable-text" and ./div[@dir="ltr"]]//span[contains(@class, "selectable-text")]
          try:
            emojis_imgs = message.find_elements_by_xpath('.//div[@class="copyable-text" and ./div[@dir="ltr" or @class="_1wlJG"]]//span[contains(@class, "selectable-text")]//img[@data-plain-text]')
            for emoji_img in emojis_imgs:
              emoji = emoji_img.get_attribute('data-plain-text')
              self.driver.execute_script("arguments[0].innerHTML = arguments[1];", emoji_img, emoji)
          except:
            pass

          try:
            #* driver.execute_script("arguments[0].innerHTML = arguments[1]", element, value)
            message_text = message.find_element_by_xpath('.//div[@class="copyable-text" and ./div[@dir="ltr" or @class="_1wlJG"]]//span[contains(@class, "selectable-text")]').get_attribute("textContent")
          except NoSuchElementException:
            message_text = None
          #except:
          #  pass
        elif type == 'audio':
          message_audio = self.read_and_save_unread_audio_message_in_chat(meta, message)
        elif type == 'document':
          message_document = self.read_and_save_unread_document_message_in_chat(meta, message)
        elif type == 'image':
          message_image = self.read_and_save_unread_image_message_in_chat(meta, message)
        elif type == 'ptt':
          message_ptt = self.read_and_save_unread_ptt_message_in_chat(meta, message)
        elif type == 'video':
          message_video = self.read_and_save_unread_video_message_in_chat(meta, message)
        else:
          return response

        #! Set return
        # TODO set read and saved to response messages

        response['messages'].append({
          '@': type,
          '@meta': meta,
          'text': message_text,
          'audio': message_audio,
          'document': message_document,
          'image': message_image,
          'ptt': message_ptt,
          'video': message_video
        })
    except TimeoutException:
      pass
    #except:
    #  pass

    return response
  ## Audio
  def read_and_save_unread_audio_message_in_chat(self, meta, message, attempts = 2, failure = 0):
    message_audio = None

    #! Download audio
    try:
      message.find_element_by_xpath('.//span[@data-icon="audio-download"]').click()
    except:
      pass

    try:
      message_audio_src = WebDriverWait(message, 5).until(
        EC.presence_of_element_located(
          (By.XPATH, './/audio')
        )
      ).get_attribute('src')

      audio_base64 = self.get_file_content_chrome(message_audio_src)
      #audio_ptt_id = message_ptt_src.replace('blob:https://web.whatsapp.com/', '')
      audio_file_relative = meta['contact_id'] + '\\' + meta['message_id'] + '.oga'

      self.create_to_save_dir(meta['contact_id'])
      attachment_saved = self.save_file_to_downloads(audio_base64, audio_file_relative)

      if audio_file_relative and attachment_saved:
        message_audio = attachment_saved
    except NoSuchElementException:
      message_audio = None
    except TimeoutException:
      message_audio = None

    if message_audio is None:
      failure = failure + 1
      if failure < attempts:
        time.sleep(1)
        return self.read_and_save_unread_audio_message_in_chat(meta, message, attempts, failure)

    return message_audio
  ## Document
  def read_and_save_unread_document_message_in_chat(self, meta, message, attempts = 2, failure = 0):
    message_document = None

    #! Download document
    try:
      message.find_element_by_xpath('.//span[@data-icon="audio-download"]').click()
    except:
      pass

    try:
      #? Get file type
      file_type = message.find_element_by_xpath('.//span[@data-meta-key="type"]').get_attribute('title').lower()
      #? Get last filename downloaded
      #downloaded = max([self.dir_downloads + "\\" + f for f in os.listdir(self.dir_downloads)], key = os.path.getctime)
      downloaded = self.get_last_downloaded_file_name()
      #? Move file downloaded to contact folder and rename with message id
      if downloaded:
        self.create_to_save_dir(meta['contact_id'])

        document_saved = f"{meta['message_id']}.{file_type}"
        to_save_relative = meta['contact_id'] + "\\" + document_saved

        try:
          shutil.move(os.path.join(self.dir_downloads, downloaded), os.path.join(self.dir_downloads, to_save_relative))
        except:
          document_saved = None
      else:
        document_saved = None

      if document_saved:
        message_document = {}
        message_document['@'] = document_saved
        message_document['type'] = file_type
    except NoSuchElementException:
      message_document = None
    except StaleElementReferenceException:
      message_document = None
    except TimeoutException:
      message_document = None

    if message_document is None:
      failure = failure + 1
      if failure < attempts:
        time.sleep(1)
        return self.read_and_save_unread_document_message_in_chat(meta, message, attempts, failure)

    return message_document
  ## Image
  def read_and_save_unread_image_message_in_chat(self, meta, message, attempts = 2, failure = 0):
    message_image = None

    #! Download media
    try:
      message.find_element_by_xpath('.//span[@data-icon="media-download"]').click()
    except:
      pass

    ## Single
    try:
      # Full image
      message_image_full_src = WebDriverWait(message, 10).until(
        EC.presence_of_element_located(
          (By.XPATH, './/div[@role="button" and @class="_1mTER" and not(.//span[contains(@data-icon, "media-")])]//img[contains(@src, "blob")]')
        )
      ).get_attribute('src')

      image_full_base64 = self.get_file_content_chrome(message_image_full_src)
      #image_id = message_image_full_src.replace('blob:https://web.whatsapp.com/', '')
      image_full_file_name = meta['contact_id'] + '\\' + meta['message_id'] + '.jpg'

      self.create_to_save_dir(meta['contact_id'])
      attachment_saved = self.save_file_to_downloads(image_full_base64, image_full_file_name)
      # Thumbnail
      # TODO get thumbnail of image
      '''
      message_image_thumb_src = WebDriverWait(message, 2).until(
        EC.presence_of_element_located(
          (By.XPATH, './/img[@class="_2ggGe _3kSha"]')
        )
      ).get_attribute('src')

      #image_id = message_image_thumb_src.replace('blob:https://web.whatsapp.com/', '')
      #image_file_name = image_id + '.jpg'

      print('message_image_thumb_src: ', message_image_thumb_src)
      img_base64 = message_image_thumb_src.replace('data:image/jpeg;base64,', '')
      #print('image_id: ', image_id)
      #print('image_file_name: ', image_file_name)

      with open(os.path.join(self.dir_downloads, 'image.jpeg'), 'wb') as image_file:
        image_file.write(base64.b64decode(img_base64))
        image_file.close()
      '''

      if image_full_file_name and attachment_saved:
        message_image = {}
        message_image['full'] = image_full_file_name
        message_image['thumbnail'] = None
    except NoSuchElementException:
      message_image = None
    except TimeoutException:
      message_image = None
    ## Album

    if message_image is None:
      failure = failure + 1
      if failure < attempts:
        time.sleep(1)
        return self.read_and_save_unread_image_message_in_chat(meta, message, attempts, failure)

    return message_image
  ## PTT
  def read_and_save_unread_ptt_message_in_chat(self, meta, message, attempts = 2, failure = 0):
    message_ptt = None

    try:
      message_ptt_src = WebDriverWait(message, 2).until(
        EC.presence_of_element_located(
          (By.XPATH, './/audio')
        )
      ).get_attribute('src')

      audio_ptt_base64 = self.get_file_content_chrome(message_ptt_src)
      #audio_ptt_id = message_ptt_src.replace('blob:https://web.whatsapp.com/', '')
      audio_ptt_file_relative = meta['contact_id'] + '\\' + meta['message_id'] + '.oga'

      self.create_to_save_dir(meta['contact_id'])
      attachment_saved = self.save_file_to_downloads(audio_ptt_base64, audio_ptt_file_relative)

      if audio_ptt_file_relative and attachment_saved:
        message_ptt = attachment_saved
    except NoSuchElementException:
      message_ptt = None
    except TimeoutException:
      message_ptt = None

    if message_ptt is None:
      failure = failure + 1
      if failure < attempts:
        time.sleep(1)
        return self.read_and_save_unread_ptt_message_in_chat(meta, message, attempts, failure)

    return message_ptt
  ## Video
  def read_and_save_unread_video_message_in_chat(self, meta, message, attempts = 3, failure = 0):
    message_video = None

    #! Download media
    try:
      message.find_element_by_xpath('.//span[@data-icon="media-download"]').click()
    except:
      pass

    try:
      #! Full video
      #? Wait 10 seconds to download and open video window
      #* .//div[@class="_2kvHM"]
      #* .//span[@data-icon="video-pip"]
      #* .//span[@data-icon="media-play"]
      WebDriverWait(message, 10).until(
        EC.presence_of_element_located(
          (By.XPATH, './/span[@data-icon="media-play"]')
        )
      ).click()

      method = 1
      if method == 1:
        #? Method 1 - Get video src with blob
        self.log('\x1b[0;37;44m' + 'Getting video src...' + '\x1b[0m' + '.')
        #* //div[@id="app"]/div/span//video[contains(@src, "blob")]
        #* //video[contains(@src, "blob")
        #* //div[@class="_3y4A-"]//video
        #* //div[@id="app"]/div/span//video[contains(@src, "blob")]
        #message_video_src = self.driver.find_element_by_xpath('//video').get_attribute('src')
        message_video_src = WebDriverWait(self.driver, 1).until(
          EC.presence_of_element_located(
            (By.XPATH, '//video')
          )
        ).get_attribute('src')
        self.log('\x1b[6;30;42m' + 'Video src:' + '\x1b[0m' + f' {message_video_src}.')
        #? Method 1 - Get and save video from blob to file
        if 'blob' in message_video_src:
          self.create_to_save_dir(meta['contact_id'])

          file_content = self.get_file_content_chrome(message_video_src)
          video_file_name = f"{meta['message_id']}.mp4"
          to_save_relative = meta['contact_id'] + '\\' + video_file_name
          attachment_saved = self.save_file_to_downloads(file_content, to_save_relative)
        else:
          video_file_name = None
      elif method == 2:
        #? Method 2 - Click to download video file
        WebDriverWait(self.driver, 1).until(
          EC.presence_of_element_located(
            (By.XPATH, '//div[@id="app"]/div/span//div[./span[@title="Download" or @data-icon="download"]]')
          )
        ).click()
        #? Method 2 - Get last filename downloaded
        #downloaded = max([self.dir_downloads + "\\" + f for f in os.listdir(self.dir_downloads)], key = os.path.getctime)
        downloaded = self.get_last_downloaded_file_name()
        #? Method 2 - Move file downloaded to contact folder and rename with message id
        if downloaded:
          to_save_dir = os.path.join(self.dir_downloads, meta['contact_id'])
          if not os.path.exists(to_save_dir):
            os.makedirs(to_save_dir)

          video_file_name = f"{meta['message_id']}.mp4"
          to_save_relative = meta['contact_id'] + "\\" + video_file_name

          shutil.move(os.path.join(self.dir_downloads, downloaded), os.path.join(self.dir_downloads, to_save_relative))
        else:
          video_file_name = None
      #? Close video dialog
      WebDriverWait(self.driver, 2).until(
        EC.presence_of_element_located(
          (By.XPATH, '//div[@id="app"]/div/span//div[./span[@title="Close" or @data-icon="x-viewer"]]')
        )
      ).click()

      if video_file_name and attachment_saved:
        message_video = {}
        message_video['full'] = video_file_name
        message_video['thumbnail'] = None
    except NoSuchElementException:
      message_video = None
    except StaleElementReferenceException:
      message_video = None
    except TimeoutException:
      message_video = None

    if message_video is None:
      failure = failure + 1
      if failure < attempts:
        time.sleep(1)
        return self.read_and_save_unread_video_message_in_chat(meta, message, attempts, failure)

    return message_video
  #? Send message
  ## Audio
  def send_message_audio_from_file(self, file_name):
    if self.chat_opened:
      try:
        self.log('\x1b[0;30;43m' + 'Sending audio from file...' + '\x1b[0m')

        # Open chat input
        self.click_to_input_chat_attach()
        # Input chat file audio
        self.input_chat_attach_audio(self.dir_uploads + '/audios/' + file_name)
        # Send audio
        WebDriverWait(self.driver, 10).until(
          EC.presence_of_element_located(
            (By.XPATH, '//div[@role="button" and @tabindex="0" and .//span[@data-icon="send"]]')
          )
        ).click()

        self.log('\x1b[6;30;42m' + f'Audio file sent:' + '\x1b[0m' + f' {file_name}')

        return True
      except ElementNotInteractableException:
        self.log('\x1b[6;30;41m' + 'Sending audio failed! [ElementNotInteractableException]' + '\x1b[0m')
        return False
      except:
        self.log('\x1b[6;30;41m' + 'Sending audio failed! [Unknown error]' + '\x1b[0m')
        return False
    else:
      return False
  ## Document
  def send_message_document_from_file(self, file_name):
    if self.chat_opened:
      try:
        self.log('\x1b[0;30;43m' + 'Sending document from file...' + '\x1b[0m')

        # Open chat input
        self.click_to_input_chat_attach()
        # Input chat file document
        self.input_chat_attach_document(self.dir_uploads + '/documents/' + file_name)
        # Send document
        WebDriverWait(self.driver, 10).until(
          EC.presence_of_element_located(
            (By.XPATH, '//div[@role="button" and @tabindex="0" and .//span[@data-icon="send"]]')
          )
        ).click()

        self.log('\x1b[6;30;42m' + f'Document file sent:' + '\x1b[0m' + f' {file_name}')

        return True
      except ElementNotInteractableException:
        self.log('\x1b[6;30;41m' + 'Sending document failed! [ElementNotInteractableException]' + '\x1b[0m')
        return False
      except:
        self.log('\x1b[6;30;41m' + 'Sending document failed! [Unknown error]' + '\x1b[0m')
        return False
    else:
      return False
  ## Image
  def send_message_image_from_file_copying_and_pasting(self, file, caption = None):
    if self.chat_opened:
      try:
        self.log('\x1b[0;30;43m' + 'Sending image from file...' + '\x1b[0m')

        output = BytesIO()
        Image.open(self.dir_uploads + '/images/' + file).convert("RGB").save(output, "BMP")
        data = output.getvalue()[14:]
        output.close()

        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
        win32clipboard.CloseClipboard()

        # Select chat input text
        input_element = self.click_to_input_chat_text()
        # Past image from clipboard
        input_element.send_keys(Keys.CONTROL, 'v')
        time.sleep(0.9)
        # Set image caption
        clipboard.copy(caption)
        input_element = self.click_to_input_chat_text()
        input_element.send_keys(Keys.CONTROL, 'v')
        # Send message
        ActionChains(self.driver).send_keys(Keys.ENTER).perform()

        self.log('\x1b[6;30;42m' + f'Image caption:' + '\x1b[0m' + f' {caption}')
        self.log('\x1b[6;30;42m' + f'Image file sent:' + '\x1b[0m' + f' {file}')

        return True
      except ElementNotInteractableException:
        self.log('\x1b[6;30;41m' + 'Sending image failed! [ElementNotInteractableException]' + '\x1b[0m')
        return False
      #except:
      #  self.log('\x1b[6;30;41m' + 'Sending image failed! [Unknown error]' + '\x1b[0m')
      #  return False
    else:
      return False
  ## Text
  def send_message_text_writing(self, message):
    if self.chat_opened:
      try:
        self.log('\x1b[0;30;43m' + 'Writing chat message...' + '\x1b[0m')

        # Select chat input text
        input_element = self.click_to_input_chat_text()
        # Write message
        for line in message.split('\n'):
          input_element.send_keys(line)
          ActionChains(self.driver).key_down(Keys.SHIFT).key_down(Keys.ENTER).key_up(Keys.SHIFT).key_up(Keys.ENTER).perform()
        # Send message
        input_element.send_keys(Keys.ENTER)
      except ElementNotInteractableException:
        self.send_message_text_writing(message)
      except:
        self.send_message_text_writing(message)
  def send_message_text(self, message, attempts = 1):
    if self.chat_opened:
      try:
        self.log('\x1b[0;30;43m' + 'Sending text message..' + '\x1b[0m' + '.')

        # Select chat input text
        input_element = self.click_to_input_chat_text()
        if input_element:
          # Copy message text to clipboard
          clipboard.copy(message)
          # Past message text from clipboard
          input_element.send_keys(Keys.CONTROL, 'v')
          # Send message
          input_element.send_keys(Keys.ENTER)

          self.log('\x1b[6;30;42m' + 'Text message sent:' + '\x1b[0m' + f' {message}')

          return True
        else:
          self.log('\x1b[6;30;41m' + 'Text message not sent:' + '\x1b[0m' + f' {message}')

          return False
      except:
        if attempts <= 3:
          return self.send_message_text(message, attempts + 1)
        else:
          return False
    else:
      return False
  def send_message_text_replying(self, message, message_id, attempts = 2, failure = 0):
    if self.chat_opened:
      try:
        self.log('\x1b[0;30;43m' + 'Sending text message as reply..' + '\x1b[0m' + '.')

        #? Click to reply
        target_message = WebDriverWait(self.driver, 1).until(
          EC.presence_of_element_located(
            (By.XPATH, f'//div[@id="app"]//div[@role="region" and contains(@aria-label, "Message list")]/div[contains(@data-id, "{message_id}")]//div[@class="_2PKDl"]')
          )
        )

        Action = ActionChains(self.driver)
        Action.move_to_element(target_message).perform()

        WebDriverWait(self.driver, 2).until(
          EC.presence_of_element_located(
            (By.XPATH, '//span[@data-testid="down-context" or @data-icon="down-context"]')
          )
        ).click()

        WebDriverWait(self.driver, 2).until(
          EC.presence_of_element_located(
            (By.XPATH, '//div[@role="button" and @title="Reply"]')
          )
        ).click()

        #? Click to input chat text
        input_element = self.click_to_input_chat_text()
        if input_element:
          # Copy message text to clipboard
          clipboard.copy(message)
          # Past message text from clipboard
          input_element.send_keys(Keys.CONTROL, 'v')
          # Send message
          input_element.send_keys(Keys.ENTER)

          self.log('\x1b[6;30;42m' + 'Text message sent:' + '\x1b[0m' + f' {message}')

          return True
        else:
          raise Exception("...") 
      except:
        self.log('\x1b[6;30;41m' + 'Trying again... Text message not sent:' + '\x1b[0m' + f' {message}')

        failure = failure + 1
        if failure < attempts:
          return self.send_message_text_replying(message, message_id, attempts, failure)
        else:
          self.log('\x1b[6;30;41m' + 'Text message not sent:' + '\x1b[0m' + f' {message}')
          return False
    else:
      return False
  ## Video
  def send_message_video_from_file(self, file_name, caption = None):
    if self.chat_opened:
      try:
        self.log('\x1b[0;30;43m' + 'Sending video from file...' + '\x1b[0m')

        # Open chat input
        self.click_to_input_chat_attach()
        # Input chat file video
        input_chat_attached = self.input_chat_attach_video(self.dir_uploads + '/videos/' + file_name)
        if input_chat_attached:
          # Set image caption
          if caption:
            clipboard.copy(caption)

            chat_input_caption = self.click_to_input_chat_caption()

            if chat_input_caption:
              chat_input_caption.send_keys(Keys.CONTROL, 'v')
          # Send video
          WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.XPATH, '//div[@role="button" and @tabindex="0" and .//span[@data-icon="send"]]'))).click()

          self.log('\x1b[6;30;42m' + f'Video caption:' + '\x1b[0m' + f' {caption}')
          self.log('\x1b[6;30;42m' + f'Video file sent:' + '\x1b[0m' + f' {file_name}')

          return True
        else:
          return False
      except ElementNotInteractableException:
        self.log('\x1b[6;30;41m' + 'Sending video failed! [ElementNotInteractableException]' + '\x1b[0m')
        WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.XPATH, '//button[not(@tabindex) and ./span[@data-icon="x"]]'))).click()
        return False
      except:
        self.log('\x1b[6;30;41m' + 'Sending video failed! [Unknown error]' + '\x1b[0m')
        WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.XPATH, '//button[not(@tabindex) and ./span[@data-icon="x"]]'))).click()
        return False
    else:
      return False
  #! Chat -> Session
  # TODO get enabled flow id to add in child('chats').child('sessions').child(self.phone_number).child('flows').child(flow_id)
  def get_chat_session(self, contact_id, index = -1):
    try:
      if index == -1: # Last session path
        last_path = database.child('chats').child('sessions').child(self.phone_number).child('flows').child(self.flow_enabled_key).child(contact_id).order_by_key().limit_to_last(1).get()
        return last_path
      elif index == 1:
        first_session = database.child('chats').child('sessions').child(self.phone_number).child('flows').child(self.flow_enabled_key).child(contact_id).order_by_key().limit_to_first(1).get()
        return first_session
    except:
      return None
  def reset_chat_session(self, contact_id):
    database.child('chats').child('sessions').child(self.phone_number).child('flows').child(self.flow_enabled_key).child(contact_id).push({
      "@": False,
      "@component": False,
      "@level": 0
    })
  def start_chat_session(self, contact_id):
    get_last_session = self.get_chat_session(contact_id, -1)

    # Create chat session if not exists
    if get_last_session is None or not get_last_session.val():
      self.reset_chat_session(contact_id)
      return self.start_chat_session(contact_id)

    # Get current session
    for get_session in get_last_session.each():
      session = get_session.val()

    self.chat_last_session = session

    return session
  def set_chat_session(self, contact_id, new_session):
    database.child('chats').child('sessions').child(self.phone_number).child('flows').child(self.flow_enabled_key).child(contact_id).push(new_session)
  def update_chat_session(self, key, value):
    pass

  #! Stream
  def setting(self, message):
    if message["path"] == "/":
      self.settings = message["data"]
    else:
      keys = message["path"][1:].split('/')

      if len(keys) == 1:
        self.settings[keys[0]] = message["data"]
      else:
        _key = keys[0]
        key_ = keys.pop()

        data = self.settings

        for key in keys:
          try: 
            int(key)
            key = int(key)
          except ValueError:
            pass

          data = data[key]

        data[key_] = message["data"]
  def executing(self, message):
    if self.bypass_stream_executing is False:
      if message["path"] == "/":
        if type(message["data"]) is dict:
          self.commands = message["data"]

          for key, command in message["data"].items():
            self.execute(key, command)
      else:
        keys = message["path"][1:].split('/')

        if len(keys) == 1:
          self.commands[keys[0]] = message["data"]
          self.execute(keys[0], message["data"])
        else:
          _key = keys[0]
          key_ = keys.pop()

          data = self.commands

          for key in keys:
            try: 
              int(key)
              key = int(key)
            except ValueError:
              pass

            data = data[key]

          data[key_] = message["data"]

          self.execute(_key, data)
    else:
      self.bypass_stream_executing = False
  def flowing(self, message):
    if message["path"] == "/":
      for key, flow in message["data"].items():
        if '!enabled' in flow and flow["!enabled"]:
          self.flow_enabled_key = key
          self.flow_enabled_data = flow
          break
    else:
      keys = message["path"][1:].split('/')

      if len(keys) == 1:
        self.flow_enabled_data[keys[0]] = message["data"]
      else:
        _key = keys[0]
        key_ = keys.pop()

        data = self.flow_enabled_data

        for key in keys:
          try: 
            int(key)
            key = int(key)
          except ValueError:
            pass

          data = data[key]

        data[key_] = message["data"]

  #! Resource
  def autorespond(self):
    try:
      for chat_item_list in self.check_and_return_unread_chats_in_chat_list():
        self.log('\x1b[0;37;44m' + 'Autoresponder - Responding unread messages..' + '\x1b[0m' + '.')

        chat = self.get_chat_item_info(chat_item_list)

        if self.open_chat(chat['@']):
          #! Get contact
          chat['contact'] = self.get_contact_info()
          #! Select contact
          self.selected_contact_name = chat['contact']['name']
          #! Get attachments and messages
          if not chat['message']['@']['text'] or chat['message']['unreads'] > 1:
            #self.log('\x1b[6;30;41m' + 'No text message or unread messages > 1' + '\x1b[0m' + '.')

            #response = self.read_and_save_last_message_in_chat(chat['message']['@']['@type'])
            #if response['messages'] is not None:
            #  chat['message']['@'] = response['messages'].pop()

            #self.log('\x1b[0;30;47m' + 'Messages received:' + '\x1b[0m')
            #print(response['messages'])
            pass
          else:
            self.log('\x1b[0;30;47m' + 'Text message received:' + '\x1b[0m' + f" {chat['message']['@']['text']}")
          #! Execute flow
          self.execute_chat_flow(chat['contact'], chat['message']['@'])
    except WebDriverException as e:
      self.log('\x1b[6;30;41m' + f'Error [WebDriverException]: {e}' + '\x1b[0m')

  #! Command
  def check(self):
    # Check internet connection offline?
    # //div[@class="pcVTC"]

    while self.on:
      if not self.authenticated:
        self.authenticate()
        time.sleep(1)
      else:
        #? Autoresponder
        if self.settings['@']['autoresponder']:
          self.autorespond()
        #TODO Scheduler
  def wait(self, seconds):
    time.sleep(seconds)
  def execute(self, key, command):
    if not self.authenticated:
      return False
    if not command:
      return False

    settings = self.settings['command']['execution']
    executing = settings['@']
    remove_after_execute = settings['remove_after_execute']
    remove_inactived_message = settings['remove_inactived_message']

    if not executing:
      return False

    if not key or key != "@":
      if ("@" not in command) or ("action" not in command) or ("payload" not in command):
        return

      action = command["action"]
      payload = command["payload"]

      if command["@"]:
        self.log('\x1b[0;37;44m' + 'Executing commands..' + '\x1b[0m' + '.')

        #self.log('\x1b[6;30;42m' + 'Key:' + '\x1b[0m', + f' {key}')
        #self.log('\x1b[6;30;42m' + 'Command:' + '\x1b[0m')
        #self.log(command)

        #self.log('\x1b[0;30;44m' + "Action:" + '\x1b[0m')
        #self.log(action)
        #self.log('\x1b[0;30;44m' + "Payload:" + '\x1b[0m')
        #self.log(payload)

        # Common
        chats = None
        if "@chats" in payload:
          chats = payload["@chats"]
        # Specific
        file = None
        if "file" in payload:
          # TODO [SECURITY] - remove ../
          file = payload["file"]
        caption = None
        if "caption" in payload:
          caption = payload["caption"]

        if chats:
          for chat in chats:
            if action == "select_contact_by_name_in_chat_list_search":
              # Select contact
              self.select_contact_by_name_in_chat_list_search(chat["name"])
            elif action == "send_message_text":
              # Select contact
              self.select_contact_by_name_in_chat_list_search(chat["name"])
              # Select text
              self.send_message_text(payload["message"])
            elif action == "send_message_image_from_file_copying_and_pasting":
              # Select contact
              self.select_contact_by_name_in_chat_list_search(chat["name"])
              # Send image
              self.send_message_image_from_file_copying_and_pasting(file, caption)
              # Wait 1 second
              time.sleep(1)
            elif action == "send_message_document_from_file":
              # Select contact
              self.select_contact_by_name_in_chat_list_search(chat["name"])
              # Send document
              self.send_message_document_from_file(file)
            elif action == "send_message_audio_from_file":
              # Select contact
              self.select_contact_by_name_in_chat_list_search(chat["name"])
              # Send audio
              self.send_message_audio_from_file(file)
            elif action == "send_message_video_from_file":
              # Select contact
              self.select_contact_by_name_in_chat_list_search(chat["name"])
              # Send video
              self.send_message_video_from_file(file, caption)

        #if settings['close_chat_after_execute']:
          #self.close_chat()

        if remove_after_execute:
          if key:
            self.bypass_stream_executing = True
            database.child('commands').child(self.phone_number).child(key).remove()
        else:
          if key:
            self.bypass_stream_executing = True
            database.child('commands').child(self.phone_number).child(key).update({ "@": False })

        self.log('\x1b[0;37;44m' + 'Commands executed' + '\x1b[0m' + '.')
        return True
      else:
        if remove_inactived_message:
          if key:
            self.bypass_stream_executing = True
            database.child('commands').child(self.phone_number).child(key).remove()

        return False



WhatsAppBot = WhatsAppBot()

try:
  WhatsAppBot.boot()
  WhatsAppBot.check()
except KeyboardInterrupt:
  print('\x1b[0;30;43m' + 'Turning off WhatsAppBot...' + '\x1b[0m' + '.')
  WhatsAppBot.shutdown()
  sys.exit()
except ConnectionError:
  print('Connection error!')
#except:
#  print('Unknown error!')
finally:
  print('\x1b[6;30;41m' + 'WhatsAppBot off.' + '\x1b[0m' + '.')
