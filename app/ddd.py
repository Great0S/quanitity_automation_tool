import re
import os
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from api.n11_rest_api import N11RestAPI
from api.n11_soap_api import N11SoapAPI
from tui import ProductManagerApp
from rich.prompt import Prompt
from typing import Dict, List, Any, Optional, Tuple
from app.config import logger
from api.amazon_seller_api import AmazonListingManager, spapi_getlistings
from api.hepsiburada_api import Hb_API
from api.pazarama_api import PazaramaAPIClient
from api.pttavm_api import getpttavm_procuctskdata, pttavm_updatedata
from api.trendyol_api import get_trendyol_stock_data, post_trendyol_data
from api.wordpress_api import create_wordpress_products, get_wordpress_products, update_wordpress_products


class App:

  def __init__(self) -> None:
    self.platform_data_cache = {}
    self.platforms = [
      "n11",
      "hepsiburada",
      "amazon",
      "pttavm",
      "pazarama",
      "trendyol",
      "wordpress",
    ]

    self.hpApi = Hb_API()
    self.n11Api = N11RestAPI()
    self.n11SApi = N11SoapAPI()
    self.amznApi = AmazonListingManager()
    self.pazaramaApi = PazaramaAPIClient()

  def filter_data(self, every_product: List[Dict[str, Any]], local: bool, targets: List[str]) -> Tuple[Dict[str, Any], List[str]]:
      """Filters and retrieves stock data for different platforms based on specified targets."""
      data_content = {}
      codes = []
      platform_to_function = {
          "n11": self.n11Api.get_products,
          "hepsiburada": self.hpApi.get_listings,
          "amazon": spapi_getlistings,
          "pttavm": getpttavm_procuctskdata,
          "pazarama": self.pazaramaApi.get_products,
          "wordpress": get_wordpress_products,
          "trendyol": get_trendyol_stock_data,
      }

      for name in targets:
          for platform, function in platform_to_function.items():
              if re.search(platform, name):
                  data_content[f"{name}_data"] = function(every_product)

      for _, item in data_content.items():
          for item_data in item:
              codes.append(item_data["sku"])

      return data_content, codes

  def filter_items(self, data: Dict[str, Any], source: str = "", use_source: bool = False,
                   target: str = "", include_all: bool = False,
                   find_mismatches: bool = False) -> List[Dict[str, Any]]:
      """Filters and compares item data across platforms."""
      if source:
          del self.platforms[self.platforms.index(source)]

      if find_mismatches:
          return self.find_non_matching_items(data, source, target)

      matching_items = {}

      for platform in self.platforms:
          platform_data = data.get(f"{platform}_data")
          if not platform_data:
              continue
            
          if use_source:
              self.compare_with_source(data[f"{source}_data"], platform_data, platform, matching_items, include_all)
          else:
              for item in platform_data:
                  self.add_items_without_source(matching_items=matching_items, target_item=item,
                                           platform=platform, include_all=include_all)

      return self.generate_changed_items(matching_items, use_source)

  def load_initial_data(self, load_all: bool, platforms: Optional[List[str]] = None) -> Dict[str, Any]:
      """Loads initial data in the background and caches it."""
      platform_functions = {
          "trendyol": lambda: get_trendyol_stock_data(load_all),
          "n11": lambda: self.n11Api.get_products(raw_data=load_all),
          "hepsiburada": lambda: self.hpApi.get_listings(load_all),
          "pazarama": lambda: self.pazaramaApi.get_products(load_all),
          "wordpress": lambda: get_wordpress_products(load_all),
          "pttavm": lambda: getpttavm_procuctskdata(load_all),
          "amazon": lambda: spapi_getlistings(load_all),
      }

      data = {}
      selected_platforms = platforms or platform_functions.keys()

      for platform in selected_platforms:
          try:
              data[platform] = platform_functions[platform]()
          except KeyError:
              logger.warning(f"Platform '{platform}' not found.")
          except Exception as e:
              logger.error(f"Error loading data for platform '{platform}': {e}")

      if platforms is None:
          self.platform_data_cache.update(data)

      return data

  def retrieve_stock_data(self, include_all_products: bool = False,
                          use_local_data: bool = False,
                          source_platform: Optional[str] = None,
                          target_platforms: Optional[List[str]] = None,
                          match_data: bool = False) -> Tuple[Dict[str, Any], List[str]]:
      """Retrieves stock data from various platforms."""
      targets = target_platforms if target_platforms else []

      try:
          source_data = self.retrieve_data(include_all_products=include_all_products,
                                            use_local_data=use_local_data,
                                            platforms=[source_platform])

          target_data = self.retrieve_data(include_all_products=include_all_products,
                                            use_local_data=use_local_data,
                                            platforms=targets)

          if source_platform:
              target_data[source_platform] = source_data[source_platform]

          return target_data

      except Exception as e:
          logger.error(f"An error occurred while retrieving stock data: {e}")

      return {}

  def process_update_data(self, source=None, use_source=False,
                          targets=None, options=None) -> Dict[str, Any]:
      """Processes stock updates from different platforms."""
      if options not in [None, "full", "info"]:
          logger.error(f"Invalid options value: {options}")
          return {}

      all_data = options in ["full", "info"]

      try:
          data_lists = self.retrieve_stock_data(include_all_products=all_data,
                                                 source_platform=source,
                                                 target_platforms=targets)

          if not data_lists:
              logger.info("No data retrieved. Exiting.")
              return {}

          platform_updates = self.filter_items(data=data_lists,
                                               source=source,
                                               use_source=use_source,
                                               target=targets,
                                               include_all=all_data)

          logger.info(f"Product updates count is {len(platform_updates)}")

          return platform_updates

      except Exception as e:
          logger.error(f"An error occurred while processing update data: {e}")

      return {}

# Additional functions and class implementations would follow a similar pattern.

if __name__ == "__main__":
    app_instance = App()
    input_app = ProductManagerApp()
    results = input_app.run()
    app_instance.process(results)
