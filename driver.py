import time
from shared import logging
from selenium import webdriver
from selenium.webdriver import DesiredCapabilities
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from pyvirtualdisplay import Display
from selenium.webdriver.support.ui import Select
from constants import *

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)


class DriverForSelenium:

    def __init__(self, username=ADMIN, password=ADMIN_PWD, host=BASEURL_DEV, customer=TEST, vis=False):
        self.visible = vis
        if not self.visible:
            self.display = Display(visible=0, size=(1920, 1080)).start()
            self.driver = webdriver.Chrome('./chromedriver')
        else:
            self.driver = webdriver.Chrome('./chromedriver')
            self.driver.maximize_window()

        self.driver.implicitly_wait(4)
        self.wait = WebDriverWait(self.driver, 8)
        self.desired_cap = DesiredCapabilities.CHROME
        self.desired_cap['loggingPrefs'] = {'browser': 'ALL'}
        self.host = host
        self.customer = customer
        self.username = username
        self.login(username, password, host, customer)

    def login(self, username, password, host, customer):
        """
        :param customer: customer name, str()
        :param username: str()
        :param password: str()
        :param host: baseurl
        :return: login to main page
        """
        if username == 'unregistered':
            return LOGGER.info('unregistered user has entered')
        else:
            xpaths = {
                "username": "//input[@id='login']",
                "password": "//input[@id='password']",
                "submit_login": "//button[@type='submit']"
            }
            self.driver.get(host)
            self.driver.find_element_by_xpath(xpaths['username']).clear()
            self.driver.find_element_by_xpath(xpaths['username']).send_keys(username)
            self.driver.find_element_by_xpath(xpaths['password']).clear()
            self.driver.find_element_by_xpath(xpaths['password']).send_keys(password)
            self.driver.find_element_by_xpath(xpaths['submit_login']).click()

            self.driver.implicitly_wait(1)
            try:
                self.driver.find_element_by_class_name('login-form-error').is_displayed()
                LOGGER.error('Login failed')
                wrong = self.driver.find_element_by_class_name('login-form-error').text
                LOGGER.error(wrong)
                self.quit()
            except NoSuchElementException:
                if username == ADMIN:
                    select = Select(self.driver.find_element_by_id('choose_client'))
                    select.select_by_visible_text(customer)
                    self.driver.find_element_by_id('choose_client_form').submit()
                LOGGER.info('Logged in as <%s> at customer <%s>' % (username, customer))
            self.driver.implicitly_wait(4)

    def edit_profile(self, **kwargs):
        """
        kwargs:
            new_name: str(), "first_name second_name"
            new_email: str()
            curr_pass: str()
            new_pass: str()
        """
        profile_btn = self.driver.find_element_by_class_name('nav_profile_container')
        profile_btn.click()
        profile_btn.find_element_by_class_name('authenticated_user_id').click()
        self.wait.until(EC.element_to_be_clickable((By.ID, 'profile_name')))
        new_name = kwargs.get('new_name')
        if new_name:
            self.driver.find_element_by_id('profile_name').clear()
            self.driver.find_element_by_id('profile_name').send_keys(new_name)
        new_email = kwargs.get('new_email')
        if new_email:
            self.driver.find_element_by_id('profile_new_login').clear()
            self.driver.find_element_by_id('profile_new_login').send_keys(new_email)
        new_pass = kwargs.get('new_pass')
        if new_pass:
            curr_pass = kwargs.get('curr_pass')
            self.driver.find_element_by_id('profile_current_password').clear()
            self.driver.find_element_by_id('profile_current_password').send_keys(curr_pass)
            self.driver.find_element_by_id('profile_new_password').clear()
            self.driver.find_element_by_id('profile_new_password').send_keys(new_pass)
        # save
        self.driver.find_element_by_id('profile_common_info_form').click()

    def create_user(self, first_name, last_name, email, role=None, groups=None):
        """
        :param first_name: str()
        :param last_name: str()
        :param email: str()
        :param role: str(), either 'reader', 'author or 'admin'
        :param groups: [str(),]
        """
        # enter settings first
        self.driver.get(self.host + '/settings?module=account&section=users')
        self.driver.find_element_by_class_name('create_new_user').click()
        self.wait.until(EC.element_to_be_clickable((By.ID, 'new_user_first_name')))
        # fill in form
        self.driver.find_element_by_id('new_user_first_name').send_keys(first_name)
        self.driver.find_element_by_id('new_user_last_name').send_keys(last_name)
        self.driver.find_element_by_id('new_user_email').send_keys(email)
        if role:
            select = Select(self.driver.find_element_by_id('new_user_role'))
            select.select_by_value(role)
        if groups:
            select = Select(self.driver.find_element_by_id('new_user_group'))
            for group in groups:
                select.select_by_visible_text(group)
        # submit
        self.wait = WebDriverWait(self.driver, 4)
        try:
            self.driver.find_element(value='new_user_form').submit()
            self.wait.until(EC.invisibility_of_element_located((By.ID, 'new_user')))
            LOGGER.info('User <%s> was created' % email)
        except TimeoutException:
            usr_exists_xpath = "//p[contains(text(), 'Пользователь с таким логином уже существует')]"
            user_exists = EC.visibility_of_element_located((By.XPATH, usr_exists_xpath))
            if user_exists:
                LOGGER.error('<SKIP> User %s already exist!' % email)
                cancel_btn_xpath = "//form[@id='new_user_form']//button[contains(text(),'Отменить')]"
                self.driver.find_element_by_xpath(cancel_btn_xpath).click()
                self.wait.until(EC.invisibility_of_element_located((By.ID, 'new_user')))
            else:
                raise TimeoutException('Failed to create user <%s>' % email)
        self.wait = WebDriverWait(self.driver, 8)

    def edit_user(self, email, **kwargs):
        """
        :param email: str()
        kwargs:
            new_name: str() "first_name second_name"
            role: if need to change, requires one of three: "supervisor", "moderator", "operator"
            new_email: str()
            new_pass: str()
            is user active: bool()
        """
        # enter profile first
        self.driver.get(self.host + 'settings?module=account&section=users')
        self.wait.until(EC.visibility_of_element_located((By.TAG_NAME, 'tbody')))
        users_table = self.driver.find_element_by_tag_name('tbody')
        users_list = users_table.find_elements_by_tag_name('tr')
        for user in users_list:
            curr_user = user.find_element_by_class_name('table_user_email').text
            if curr_user == email:
                user.click()
                # handle inactivity
                self.wait.until(EC.visibility_of_element_located((By.ID, 'profile_name')))
                try:
                    self.driver.implicitly_wait(1)
                    inactive = self.driver.find_element_by_id('unblock_user').is_enabled()
                except NoSuchElementException:
                    inactive = False
                self.driver.implicitly_wait(4)

                active = kwargs.get('active')
                if isinstance(active, bool):
                    # unblock blocked
                    if inactive and active:
                        self.driver.find_element_by_id('unblock_user').click()
                        self.wait.until(EC.visibility_of_element_located((By.ID, 'modal_confirm_form')))
                        self.driver.find_element_by_id('modal_confirm_form').submit()
                        self.wait.until(EC.invisibility_of_element_located((By.ID, 'modal_confirm')))
                    # block unblocked
                    elif not inactive and not active:
                        self.driver.find_element_by_id('block_user').click()
                        self.wait.until(EC.visibility_of_element_located((By.ID, 'modal_confirm_form')))
                        self.driver.find_element_by_id('modal_confirm_form').submit()
                        self.wait.until(EC.invisibility_of_element_located((By.ID, 'modal_confirm')))
                else:
                    if inactive:
                        return LOGGER.error('user is inactive')
                # new name
                new_name = kwargs.get('new_name')
                if new_name:
                    self.driver.find_element_by_id('profile_name').clear()
                    self.driver.find_element_by_id('profile_name').send_keys(new_name)
                # new role
                role = kwargs.get('role')
                if role:
                    select = Select(self.driver.find_element_by_id('profile_role'))
                    select.select_by_value(role)
                # new_email
                new_email = kwargs.get('new_email')
                if new_email:
                    self.driver.find_element_by_id('profile_new_login').send_keys(new_email)
                # new_password
                new_pass = kwargs.get('new_pass')
                if new_pass:
                    self.driver.find_element_by_id('profile_new_password').clear()
                    self.driver.find_element_by_id('profile_new_password').send_keys(new_pass)
                # submit
                LOGGER.info('User <%s> was edited' % email)
                self.driver.find_element_by_id('profile_common_info_form').submit()
                break

    def create_team(self, name, users=None):
        """
        :param name: str()
        :param users: [str(),], where str like 'first_name second name'
        """
        # enter profile first
        self.driver.get(self.host + '/settings?module=account&section=users')
        teams_btn_xpath = "//li[contains(text(), 'Группы')]"
        self.driver.find_element_by_xpath(teams_btn_xpath).click()
        self.driver.find_element_by_class_name('create_new_group').click()
        # fill in the form
        self.wait.until(EC.visibility_of_element_located((By.ID, 'modal_group_form')))
        self.driver.find_element_by_id('group_title').send_keys(name)
        select = Select(self.driver.find_element_by_id('group_users'))
        if users:
            for user in users:
                select.select_by_visible_text(user)

        LOGGER.info('Group <%s> was created' % name)
        self.driver.find_element_by_id('modal_group_form').submit()
        self.wait.until(EC.visibility_of_element_located((By.ID, 'modal_group')))

    def edit_team(self, name, **kwargs):
        """
        :param name: str()
        kwargs:
            new_name: str()
            users_to_add: [str(),], where str like 'first_name second name'
            users_to_del: [str(),], where str like 'first_name second name'
            delete: bool()
        """
        # enter profile first
        self.driver.get(self.host + '/settings?module=account&section=users')
        teams_btn_xpath = "//li[contains(text(), 'Группы')]"
        self.driver.find_element_by_xpath(teams_btn_xpath).click()
        all_groups = self.driver.find_elements_by_class_name('group_item')
        for group in all_groups:
            group_name = group.find_element_by_tag_name('h6').text
            if group_name == name:
                group.click()
                self.wait.until(EC.visibility_of_element_located((By.ID, 'modal_group_form')))
                delete = kwargs.get('delete')
                if delete:
                    self.driver.find_element_by_id('remove_group').click()
                    self.driver.find_element_by_id('modal_confirm_form').submit()
                    self.wait.until(EC.invisibility_of_element_located((By.ID, 'modal_group_form')))
                    return LOGGER.info('Group <%s> was deleted' % name)

                new_name = kwargs.get('new_name')
                if new_name:
                    self.driver.find_element_by_id('group_title').clear()
                    self.driver.find_element_by_id('group_title').send_keys(new_name)
                select = Select(self.driver.find_element_by_id('group_users'))
                users_to_add = kwargs.get('users_to_add')
                if users_to_add:
                    for user in users_to_add:
                        select.select_by_visible_text(user)
                users_to_del = kwargs.get('users_to_del')
                if users_to_del:
                    for user in users_to_del:
                        select.select_by_visible_text(user)
                # submit
                self.driver.find_element_by_id('modal_group_form').submit()

        self.wait.until(EC.invisibility_of_element_located((By.ID, 'modal_group')))
        return LOGGER.info('Group <%s> was edited' % name)

    def create_collection(self, name, vis=None, loc=None, groups=None):
        """
        :param name: str()
        :param vis: visibility, str(), either 'open', 'link' or 'private'
        :param loc: location str()
        :param groups: list(), set groups to see the collection
        """
        # enter kb first
        if "/knowledge_base" not in self.driver.current_url:
            self.driver.get(self.host + 'knowledge_base?tab=structure')
        add_btn_xpath = "//button[contains(text(),'Создать')]"
        self.wait.until(EC.element_to_be_clickable((By.XPATH, add_btn_xpath)))
        self.driver.find_element_by_xpath(add_btn_xpath).click()
        self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, 'new_collection')))
        self.driver.find_element_by_class_name('new_collection').click()
        self.wait.until(EC.element_to_be_clickable((By.ID, 'collection_title')))
        self.driver.find_element_by_id('collection_title').send_keys(name)
        # set visibility
        if vis:
            select = Select(self.driver.find_element_by_id('collection_visibility'))
            if vis == 'open':
                select.select_by_value('1')
            elif vis == 'link':
                select.select_by_value('2')
            elif vis == 'private':
                select.select_by_value('3')
        # set location
        if loc:
            select = Select(self.driver.find_element_by_id('parent_collection'))
            select.select_by_visible_text(loc)
        # set teams
        if groups and vis == 'private':
            select = Select(self.driver.find_element_by_id('collection_groups'))
            for group in groups:
                select.select_by_visible_text(group)
        # save
        LOGGER.info('Collection <%s> was created' % name)
        self.driver.find_element_by_id('modal_collection_form').submit()
        self.wait.until(EC.invisibility_of_element_located((By.ID, 'modal_collection')))

    def edit_collection(self, name, **kwargs):
        """
        :param name: str()
        Kwargs:
            new_name: str()
            vis: visibility, str(), either 'open', 'link' or 'private'
            loc: location str()
            delete: bool()
        """
        # enter kb first
        self.driver.find_element_by_class_name('nav_header').click()
        self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, 'structure_list_item')))
        # # search  # todo search doesn't work yet, uncomment when it will
        # self.driver.find_element_by_id('kb_input_search').clear()
        # self.driver.find_element_by_id('kb_input_search').send_keys(name)
        # self.driver.find_element_by_id('kb_input_search').send_keys(Keys.ENTER)
        # time.sleep(0.6)  # wait to show search results

        collections = self.driver.find_elements_by_class_name('structure_list_item')
        for coll in collections:
            coll_name = coll.find_element_by_class_name('title').text
            if coll_name == name:
                # delete
                delete = kwargs.get('delete')
                if delete:
                    coll.find_element_by_class_name('indicator').click()
                    action_btn_xpath = "//button[contains(text(),'Выберите действие')]"
                    self.driver.find_element_by_xpath(action_btn_xpath).click()
                    self.driver.find_element_by_id('delete').click()
                    # confirm
                    self.wait.until(EC.visibility_of_element_located((By.ID, 'modal_confirm')))
                    self.driver.find_element_by_id('modal_confirm_form').submit()
                    self.wait.until(EC.invisibility_of_element_located((By.ID, 'modal_confirm')))
                    LOGGER.info('Collection <%s> was deleted' % name)
                    break

                coll.find_element_by_class_name('edit_collection').click()
                self.wait.until(EC.element_to_be_clickable((By.ID, 'collection_title')))
                # new name
                name_new = kwargs.get('new_name')
                if name_new:
                    self.driver.find_element_by_id('collection_title').clear()
                    self.driver.find_element_by_id('collection_title').send_keys(name_new)
                # set visibility
                visibility = kwargs.get('vis')
                if visibility:
                    select = Select(self.driver.find_element_by_id('collection_visibility'))
                    if visibility == 'open':
                        select.select_by_value('1')
                    elif visibility == 'link':
                        select.select_by_value('2')
                    elif visibility == 'private':
                        select.select_by_value('3')
                # set location
                location = kwargs.get('loc')
                if location:
                    select = Select(self.driver.find_element_by_id('parent_collection'))
                    select.select_by_visible_text(location)
                # save
                self.driver.find_element_by_id('modal_collection_form').submit()
                LOGGER.info('Collection <%s> was edited' % name)
                break

        self.wait.until(EC.invisibility_of_element_located((By.ID, 'modal_collection')))

    def create_article(self, name, **kwargs):
        """
        :param name: str()
        Kwargs:
            status: str(), 'published' or 'drafted'
            vis: visibility, str(), either 'open', 'link' or 'private'
            loc: location str()
            author: str()
            tags: list() of str() values
            text: text of the article str()
            delete: bool()
        :return created article
        """
        self.driver.get(self.host + 'new_article_v2')

        self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, 'article_name')))
        # change name
        self.driver.find_element_by_class_name('article_name').clear()
        self.driver.find_element_by_class_name('article_name').send_keys(name)
        # select article status
        status = kwargs.get('status')
        if status:
            select = Select(self.driver.find_element_by_id('article_status'))
            if status == 'published':
                select.select_by_value('0')
            elif status == 'drafted':
                select.select_by_value('1')
        # set visibility
        visibility = kwargs.get('vis')
        if visibility:
            select = Select(self.driver.find_element_by_id('article_visibility'))
            if visibility == 'open':
                select.select_by_value('1')
            elif visibility == 'link':
                select.select_by_value('2')
            elif visibility == 'private':
                select.select_by_value('3')
        # set location
        location = kwargs.get('loc')
        if location:
            select = Select(self.driver.find_element_by_id('article_collection'))
            select.select_by_visible_text(location)
        # set article author
        author = kwargs.get('author')
        if author:
            select = Select(self.driver.find_element_by_id('article_author'))
            select.select_by_visible_text(author)
        # write tags
        tags = kwargs.get('tags')
        if tags:
            for tag in tags:
                tag_field = self.driver.find_element_by_id('article_tags-selectized')
                tag_field.send_keys(tag)
                tag_field.send_keys(Keys.ENTER)
        # enter text
        text = kwargs.get('text')
        if text:
            text_field = self.driver.find_element_by_xpath("//div[@class='fr-element fr-view']")
            text_field.clear()
            text_field.send_keys(text)
        # save
        self.driver.find_element_by_id('submit_article').click()
        self.wait.until(EC.invisibility_of_element_located((By.ID, 'article_name')))
        LOGGER.info('Article <%s> was created' % name)

    def edit_article(self, name, **kwargs):
        """
        :param name: str()
        Kwargs:
            new_name: str()
            status: str(), 'published' or 'drafted'
            vis: visibility, str(), either 'open', 'link' or 'private'
            loc: location str()
            author: str()
            tags: list() of str() values
            text: text of the article str()
            delete: bool()
        :return edited article
        """
        # enter kb first
        if "/knowledge_base" not in self.driver.current_url:
            self.driver.find_element_by_class_name('nav_header').click()
        # search
        self.driver.find_element_by_id('kb_input_search').clear()
        self.driver.find_element_by_id('kb_input_search').send_keys(name)
        self.driver.find_element_by_id('kb_input_search').send_keys(Keys.ENTER)
        time.sleep(1)  # wait to show search results

        articles = self.driver.find_elements_by_class_name('structure_list_item')

        for article in articles:
            art_name = article.find_element_by_class_name('title').text
            if art_name == name:
                article.find_element_by_class_name('edit_button_container').click()
                self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, 'article_name')))
                # change name
                new_name = kwargs.get('new_name')
                if new_name:
                    self.driver.find_element_by_class_name('article_name').clear()
                    self.driver.find_element_by_class_name('article_name').send_keys(new_name)
                # select article status
                status = kwargs.get('status')
                if status:
                    select = Select(self.driver.find_element_by_id('article_status'))
                    if status == 'published':
                        select.select_by_value('0')
                    elif status == 'drafted':
                        select.select_by_value('1')
                # set visibility
                visibility = kwargs.get('vis')
                if visibility:
                    select = Select(self.driver.find_element_by_id('article_visibility'))
                    if visibility == 'open':
                        select.select_by_value('1')
                    elif visibility == 'link':
                        select.select_by_value('2')
                    elif visibility == 'private':
                        select.select_by_value('3')
                # set location
                location = kwargs.get('loc')
                if location:
                    select = Select(self.driver.find_element_by_id('article_collection'))
                    select.select_by_visible_text(location)
                # set article author
                author = kwargs.get('author')
                if author:
                    select = Select(self.driver.find_element_by_id('article_author'))
                    select.select_by_visible_text(author)
                # write tags
                tags = kwargs.get('tags')
                if tags:
                    for tag in tags:
                        tag_field = self.driver.find_element_by_id('article_tags-selectized')
                        tag_field.send_keys(tag)
                        tag_field.send_keys(Keys.ENTER)
                # enter text
                text = kwargs.get('text')
                if text:
                    text_field = self.driver.find_element_by_xpath("//div[@class='fr-element fr-view']")
                    text_field.clear()
                    text_field.send_keys(text)
                # delete
                delete = kwargs.get('delete')
                if delete:
                    self.driver.find_element_by_class_name('nt-dropdown').click()
                    self.driver.find_element_by_class_name('delete_article').click()
                    # handle alert
                    self.driver.find_element_by_id('modal_confirm_form').submit()
                    LOGGER.info('Article <%s> is deleted' % name)
                    break
                else:
                    # save
                    self.driver.find_element_by_id('submit_article').click()
                    LOGGER.info('Article <%s> was successfully edited' % name)
                    break

        self.wait.until(EC.invisibility_of_element_located((By.ID, 'article_name')))

    def register_customer(self, company_name, first_name, last_name, email, phone_number):
        """
        :param company_name: str()
        :param first_name: str()
        :param last_name: str()
        :param email: str()
        :param phone_number: str()
        """
        self.driver.get(self.host + SIGN_UP)
        self.wait.until(EC.element_to_be_clickable((By.ID, 'web_site')))
        form = self.driver.find_element_by_id('sign_up')
        # enter company_name
        form.find_element_by_id('web_site').clear()
        form.find_element_by_id('web_site').send_keys(company_name)
        # enter first & last name
        full_name = '%s %s' % (first_name, last_name)
        form.find_element_by_id('full_name').clear()
        form.find_element_by_id('full_name').send_keys(full_name)
        # enter email
        form.find_element_by_id('email').clear()
        form.find_element_by_id('email').send_keys(email)
        # enter phone number
        from phonenumbers import parse
        county_code = '+%s' % parse(phone_number).country_code
        nat_number = parse(phone_number).national_number
        select_code = Select(form.find_element_by_id('phone_country_selector'))
        select_code.select_by_value(county_code)
        form.find_element_by_id('sing_up_phone').clear()
        form.find_element_by_id('sing_up_phone').send_keys(nat_number)
        self.wait = WebDriverWait(self.driver, 4)
        form.submit()
        try:
            self.wait.until(EC.invisibility_of_element_located((By.ID, 'sign_up')))
            LOGGER.info('Customer <%s> was successfully registered' % company_name)
        except TimeoutException:
            LOGGER.error('<SKIP> Customer <%s> was not registered' % company_name)
        self.wait = WebDriverWait(self.driver, 8)

    def logout(self):
        profile_btn = self.driver.find_element_by_class_name('nav_profile_container')
        profile_btn.click()
        self.wait.until(EC.element_to_be_clickable((By.XPATH, "//a[@href='/logout']")))
        self.driver.find_element_by_xpath("//a[@href='/logout']").click()
        self.wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@id='username']")))
        LOGGER.info("User <%s> logged out" % self.username)

    def quit(self):
        self.driver.quit()
        if not self.visible:
            self.display.stop()
        LOGGER.info('Driver of user <%s> at customer <%s> has quited' % (self.username, self.customer))


if __name__ == '__main__':
    pass
