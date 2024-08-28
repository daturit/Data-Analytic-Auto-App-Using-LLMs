import undetected_chromedriver as uc
import time 
import xlwt
import os
import random
import traceback
import re
import xlrd

from xlwt import Workbook
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from datetime import date
from urllib.parse import urlparse

# Define variable
output_file_name = "batdongsan_chungcu_hcm"
crawl_url = "https://batdongsan.com.vn/ban-can-ho-chung-cu-tp-hcm" # without /
num_of_pages = 105

def get_listing_data(url):
    driver.get(url)
    time.sleep(3)
    scroll_to_bottom()
    time.sleep(2)

    lst = [element.get_attribute("href") for element in driver.find_elements(By.CSS_SELECTOR, "#product-lists-web a.js__product-link-for-product-id")]
    return lst

def convert_price(price_str, area_str):
    if 'tỷ/m²' in price_str:
        if not area_str:
            return 0
        price_str = price_str.replace('tỷ/m²', '').strip().replace(',', '.')
        return float(area_str) * float(price_str) * 1e9
    if 'triệu/m²' in price_str:
        if not area_str:
            return 0
        price_str = price_str.replace('triệu/m²', '').strip().replace(',', '.')
        return float(area_str) * float(price_str) * 1e6
    if 'tỷ' in price_str:
        price_str = price_str.replace('tỷ', '').strip().replace(',', '.')
        return float(price_str) * 1e9
    if 'triệu' in price_str:
        price_str = price_str.replace('triệu', '').strip().replace(',', '.')
        return float(price_str) * 1e6
    return 0

def scroll_to_bottom():
    scroll_position = 0.75 * driver.execute_script("return document.body.scrollHeight")
    driver.execute_script(f"window.scrollTo(0, {scroll_position});")

def save_html(content, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)

def element_has_text(locator, text):
    def _predicate(driver):
        element = driver.find_element(*locator)
        return element.text != '' and element.text != text
    return _predicate

def scroll_to_element(driver, locator):
    element = driver.find_element(*locator)
    driver.execute_script("arguments[0].scrollIntoView(true);", element)

def convert_length(length_str):
    if 'km' in length_str:
        length_str = length_str.replace('km', '').strip().replace(',', '.')
        return str(float(length_str) * 1e3)
    if 'm' in length_str:
        length_str = length_str.replace('m', '').strip().replace(',', '.')
        return str(float(length_str))
    return length_str

def extract_ma_tin_from_url(url):
    match = re.search(r"-pr(\d+)", url)
    if match:
        return match.group(1)  # Returns only the numeric part
    return None  # Return None if no "Ma Tin" is found

# Init headers
headers = [
    "Ngay dang", "Ma Tin", "Link", "Loai Tin", "Tieu De",
    "Tinh/Thanh pho", "Quan/Huyen", "Du an", "Đia chi", "Vi do", "Kinh do",
    "Nguoi đang", "So dien thoại", "Gia RAW", "Gia (VND)", "Dien tich (m2)", "So phong ngu",
    "So phong ve sinh", "So tang", "Duong vao", "Mat tien", "Huong nha", "Huong ban cong", "Noi that", "Phap ly"
]

driver = uc.Chrome()
today = date.today()

# Load existing Excel file to get already crawled "Ma Tin"
existing_ids = set()
try:
    book = xlrd.open_workbook(output_file_name + '_old.xlsx')
    first_sheet = book.sheet_by_index(0)
    ids_col_idx = headers.index("Ma Tin")  # Make sure this matches your file structure
    existing_ids = {first_sheet.cell(row, ids_col_idx).value for row in range(1, first_sheet.nrows)}
    print(existing_ids)
    print(f"Loaded {len(existing_ids)} existing IDs.")
except Exception as e:
    print("Could not load existing IDs, assuming none exist:", e)

wb = Workbook()
sheet1 = wb.add_sheet('Sheet 1')

cnt = 0
for col, header in enumerate(headers):
    sheet1.write(cnt, col, header)
cnt += 1

# Parse domain
parsed_url = urlparse(crawl_url)
crawl_domain = f"{parsed_url.scheme}://{parsed_url.netloc}"

# Output file with Extension
output_file = f"{output_file_name}.xlsx"

# Directory to save HTML files
html_dir = 'html_pages'
os.makedirs(html_dir, exist_ok=True)

# Loop through multiple pages
for page_num in range(1, num_of_pages):  # Adjust the range as needed
    print(f'START CRAWLING PAGE: {page_num}')
    base_url = f'{crawl_url}/p{page_num}'
    listings = get_listing_data(base_url)

    for itm in listings:
        if itm == None or itm == "" or crawl_domain not in itm:
            continue

        ma_tin = extract_ma_tin_from_url(itm)
        if ma_tin is not None and ma_tin in existing_ids:
            print(f"Skipping already crawled ID: {ma_tin}")
            continue  # Skip this listing if it's already been crawled

        start = time.time()
        try:
            print("Crawling item: " + itm)
            driver.get(itm) # go to each detail page
            time.sleep(0.5)
            # scroll_to_bottom()
            # time.sleep(2)
        except:
            print(itm)
            wb.save(output_file)

        try:

            # Scroll to the 'Đặc điểm bất động sản' section
            specs_locator = (By.CSS_SELECTOR, ".re__pr-specs")
            scroll_to_element(driver, specs_locator)
            # time.sleep(2)  # Give some time for the scroll to complete

            try:
                locator = (By.XPATH, "//div[contains(@class, 're__pr-short-info-item')]/span[contains(text(),'Mã tin')]/following-sibling::span")
                WebDriverWait(driver, 10).until(element_has_text(locator, ''))
                listing_id_element = driver.find_element(*locator)
                listing_id = listing_id_element.text if listing_id_element.text else ''
                if not listing_id:
                    print(f"Retry get Listing ID")
                    scroll_to_element(driver, specs_locator)
                    save_html(driver.page_source, os.path.join(html_dir, f'{cnt}_error_1.html'))
                    WebDriverWait(driver, 10).until(element_has_text(locator, ''))
                    listing_id_element = driver.find_element(*locator)
                    listing_id = listing_id_element.text if listing_id_element.text else ''
                    if not listing_id:
                        print(f"Cannot get Listing ID, SKIP 1")
                        save_html(driver.page_source, os.path.join(html_dir, f'{cnt}_error_2.html'))
                        continue
            except Exception as e1:
                print(e1)
                print('Waiting more 5s')
                time.sleep(5)
                try:
                    scroll_to_element(driver, specs_locator)
                    WebDriverWait(driver, 10).until(element_has_text(locator, ''))
                    listing_id_element = driver.find_element(*locator)
                    listing_id = listing_id_element.text if listing_id_element.text else ''
                    if not listing_id:
                        print(f"Retry get Listing ID")
                        scroll_to_element(driver, specs_locator)
                        save_html(driver.page_source, os.path.join(html_dir, f'{cnt}_error_3.html'))
                        WebDriverWait(driver, 10).until(element_has_text(locator, ''))
                        listing_id_element = driver.find_element(*locator)
                        listing_id = listing_id_element.text if listing_id_element.text else ''
                        if not listing_id:
                            print(f"Cannot get Listing ID, SKIP 2")
                            save_html(driver.page_source, os.path.join(html_dir, f'{cnt}_error_4.html'))
                except Exception as e1:
                    listing_id = ''

            if not listing_id:
                print(f"Cannot get Listing ID, SKIP 3")
                save_html(driver.page_source, os.path.join(html_dir, f'{cnt}_error_5.html'))
                continue

            
            print("Wait first item has data...")
            locator = (By.XPATH, "(//div[contains(@class, 're__pr-short-info-item')])[1]/span[2]")
            WebDriverWait(driver, 10).until(element_has_text(locator, ''))

            test_element = driver.find_element(*locator)
            test_data = test_element.text if test_element.text else ''
            print(f"First data: {test_data}")

            title = driver.find_element(By.CSS_SELECTOR, "h1[class*=title]").text
            path_menu = driver.find_element(By.CSS_SELECTOR, "[class*=re__breadcrumb]").text

            prop_type = None
            province = None
            district = None

            try:
                path_menu_lst = path_menu.split("/")
                prop_type = path_menu_lst[0]
                province = path_menu_lst[1]
                district = path_menu_lst[2]
            except:
                prop_type = ''
                province = ''
                district = ''

            address = driver.find_element(By.CSS_SELECTOR, "h1 + span").text

            phone_number = None
            try:
                phone_number = driver.find_element(By.CSS_SELECTOR, "[class*=js__phone] > span").text
                phone_number = phone_number.replace(" · Hiện số", "")
            except: 
                phone_number = ''

            owner = None
            try:
                owner = driver.find_element(By.CSS_SELECTOR, "[class*=re__contact-name] > a").text
            except:
                owner = ''

            project = None
            try:
                project = driver.find_element(By.CSS_SELECTOR, "[class*=re__project-title]").text
            except:
                project = ''

            # Extract additional fields

            area = None
            try:
                area = driver.find_element(By.XPATH, "//div[contains(@class, 're__pr-specs-content-item')]/span[contains(text(),'Diện tích')]/following-sibling::span").text
                area = area.replace(" m²", "")
            except:
                area = ''

            price = None
            price_str = None
            try:
                price_str = driver.find_element(By.XPATH, "//div[contains(@class, 're__pr-specs-content-item')]/span[contains(text(),'Mức giá')]/following-sibling::span").text
                price_number = convert_price(price_str, area)
                price = str(price_number) if price_number != 0 else price_str
            except:
                price = ''
                price_str = ''

            bedrooms = None
            try:
                bedrooms = driver.find_element(By.XPATH, "//div[contains(@class, 're__pr-specs-content-item')]/span[contains(text(),'Số phòng ngủ')]/following-sibling::span").text
                bedrooms = bedrooms.replace(" phòng", "")
            except:
                bedrooms = ''

            try:
                direction_house = driver.find_element(By.XPATH, "//div[contains(@class, 're__pr-specs-content-item')]/span[contains(text(),'Hướng nhà')]/following-sibling::span").text
            except:
                direction_house = ''

            try:
                direction_balcony = driver.find_element(By.XPATH, "//div[contains(@class, 're__pr-specs-content-item')]/span[contains(text(),'Hướng ban công')]/following-sibling::span").text
            except:
                direction_balcony = ''

            try:
                toilets = driver.find_element(By.XPATH, "//div[contains(@class, 're__pr-specs-content-item')]/span[contains(text(),'Số toilet')]/following-sibling::span").text
                toilets = toilets.replace(" phòng", "")
            except:
                toilets = ''

            try:
                interior = driver.find_element(By.XPATH, "//div[contains(@class, 're__pr-specs-content-item')]/span[contains(text(),'Nội thất')]/following-sibling::span").text
            except:
                interior = ''

            try:
                posted_date = driver.find_element(By.XPATH, "//div[contains(@class, 're__pr-short-info-item')]/span[contains(text(),'Ngày đăng')]/following-sibling::span").text
            except:
                posted_date = ''
            
            try:
                so_tang = driver.find_element(By.XPATH, "//div[contains(@class, 're__pr-specs-content-item')]/span[contains(text(),'Số tầng')]/following-sibling::span").text
                so_tang = so_tang.replace(" tầng", "")
            except:
                so_tang = ''

            try:
                duong_vao = driver.find_element(By.XPATH, "//div[contains(@class, 're__pr-specs-content-item')]/span[contains(text(),'Đường vào')]/following-sibling::span").text
                duong_vao = convert_length(duong_vao)
            except:
                duong_vao = ''

            try:
                mat_tien = driver.find_element(By.XPATH, "//div[contains(@class, 're__pr-specs-content-item')]/span[contains(text(),'Mặt tiền')]/following-sibling::span").text
                mat_tien = convert_length(mat_tien)
            except:
                mat_tien = ''

            try:
                phap_ly = driver.find_element(By.XPATH, "//div[contains(@class, 're__pr-specs-content-item')]/span[contains(text(),'Pháp lý')]/following-sibling::span").text
            except:
                phap_ly = ''

            # Wait for the iframe to be present and switch to it
            latitude = None
            longitude = None
            try:
                iframeElement = driver.find_element(By.XPATH, "//div[contains(@class, 're__pr-map')]/span[contains(text(),'Xem trên bản đồ')]/following-sibling::div/iframe")
                iframeUrl = iframeElement.get_attribute('data-src')

                # Split the URL to extract the part containing the coordinates
                coordinate_part = iframeUrl.split("q=")[1].split("&")[0]
                latitude, longitude = coordinate_part.split(",")
            except Exception as latEx:
                latitude = ''
                longitude = ''
            
            print("Page: " + str(page_num) + " - Count: " + str(cnt))
            print("ID: " + listing_id)
            print("Prop Type: " + prop_type)
            print("Title: " + title)
            print("Project: " + project)
            print("Address: " + address)
            print("Phone Number: " + phone_number)
            print("Owner: " + owner)
            print("Price: " + price)
            print("Area: " + area)
            print("Bedrooms: " + bedrooms)
            print("Toilets: " + toilets)
            print("So tang: " + so_tang)
            print("Duong vao: " + duong_vao)
            print("Mat tien: " + mat_tien)
            print("Phap ly: " + phap_ly)
            print("Toa do: " + latitude + " " + longitude)
            print("====================================")

            column = 0
            sheet1.write(cnt, column, posted_date)
            column += 1
            sheet1.write(cnt, column, listing_id)
            column += 1
            sheet1.write(cnt, column, itm)
            column += 1
            sheet1.write(cnt, column, prop_type)
            column += 1
            sheet1.write(cnt, column, title)
            column += 1
            sheet1.write(cnt, column, province)
            column += 1
            sheet1.write(cnt, column, district)
            column += 1
            sheet1.write(cnt, column, project)
            column += 1
            sheet1.write(cnt, column, address)
            column += 1
            sheet1.write(cnt, column, latitude)
            column += 1
            sheet1.write(cnt, column, longitude)
            column += 1
            sheet1.write(cnt, column, owner)
            column += 1
            sheet1.write(cnt, column, phone_number)
            column += 1
            sheet1.write(cnt, column, price_str)
            column += 1
            sheet1.write(cnt, column, price)
            column += 1
            sheet1.write(cnt, column, area)
            column += 1
            sheet1.write(cnt, column, bedrooms)
            column += 1
            sheet1.write(cnt, column, toilets)
            column += 1
            sheet1.write(cnt, column, so_tang)
            column += 1
            sheet1.write(cnt, column, duong_vao)
            column += 1
            sheet1.write(cnt, column, mat_tien)
            column += 1
            sheet1.write(cnt, column, direction_house)
            column += 1
            sheet1.write(cnt, column, direction_balcony)
            column += 1
            sheet1.write(cnt, column, interior)
            column += 1
            sheet1.write(cnt, column, phap_ly)
            column += 1

            cnt += 1

        except Exception as eTotal:
            print(f"Error at item: {itm}")
            traceback.print_exc()
            wb.save(output_file)
            print(eTotal)
        end = time.time()
        print('Completed is %f seconds.' % (end - start))

    print(f"Saving data to {output_file}")
    wb.save(output_file)

print("Close driver")
driver.close()
