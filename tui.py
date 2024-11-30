from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Label, RadioSet, RadioButton, Input, Log, Button


class ProductManagerApp(App[str]):

    CSS_PATH = "styles.tcss"
    TITLE = "Product Manager"
    SUB_TITLE = "Product Manager User Interface"

    def on_mount(self) -> None:

        self.source = ''
        self.target = ''
        self.target_options = ''
        self.sku_input = ''
        self.hide_containers([
            "create_container",
            "copy_container",
            "copy_source_container",
            "copy_target_container",
            "update_container",
            "specific_update_op_container",
            "specific_sku_op_container",
            "specific_partial_op_choice_container",
            "compare_container",
            "specific_partial_op_source_platform_container",
            "specific_partial_op_target_platform_container"
        ])

    def compose(self) -> ComposeResult:

        with VerticalScroll():

            with Horizontal(id="operation_container"):

                yield Label("What operation would you like to perform?")
                with RadioSet(id="operation_choice"):
                    yield RadioButton("Create new product", id="create")
                    yield RadioButton("Update existing product", id="update")

            with Horizontal(id="create_container"):

                yield Label("How would you like to create a new product?")
                with RadioSet(id="create_choice"):
                    yield RadioButton("Copy from another platform", id="auto_copy")
                    yield RadioButton("Enter details manually", id="manual_copy")

            with Horizontal(id="copy_container"):

                with Horizontal(id="copy_source_container"):

                    yield Label("Please select the source platform to copy from: Ex. Trendyol")
                    with RadioSet(id="copy_source_platform"):
                        for button in self.platform_radio_set():
                            yield button

                with Horizontal(id="copy_target_container"):

                    yield Label("Please enter the target platform to copy to: Ex. PTTAVM")
                    with RadioSet(id="copy_target_platform"):
                        for button in self.platform_radio_set():
                            yield button

            with Horizontal(id="compare_container"):

                yield Label("How do you want to copy the products?")
                with RadioSet(id="compare_choice"):
                    yield RadioButton("Check exisiting and copy", id="check_exisiting_and_copy")
                    yield RadioButton("Copy directly", id="copy_directly")

            with Horizontal(id="update_container"):

                yield Label("Do you want to update specific platforms?")
                with RadioSet(id="update_choice"):
                    yield RadioButton("Yes", id="yes_specific_update")
                    yield RadioButton("No", id="no_specific_update")

            with Horizontal(id="specific_update_op_container"):

                yield Label("Available operations:")
                with RadioSet(id="specific_update_op_choice"):
                    yield RadioButton("Full update", id="specific_full_update")
                    yield RadioButton("Partial update", id="specific_partial_update")
                    yield RadioButton("By SKU update", id="specific_sku_update")
            
            with Horizontal(id="specific_sku_op_container"):

                yield Input(placeholder="Enter SKU or SKU list with comma between each SKU", id="specific_sku_input")
                yield Input(placeholder="Enter the values to be updated with comma between each value", id="specific_sku_value_input")
                yield Button(label="Submit", id="specific_sku_submit_button")

            with Horizontal(id="specific_partial_op_source_platform_container"):

                yield Label("Please select the source platform to copy from: Ex. Trendyol")
                with RadioSet(id="specific_partial_op_source_platform"):
                    for button in self.platform_radio_set():
                        yield button

            with Horizontal(id="specific_partial_op_target_platform_container"):

                yield Label("Please select the target platform: Ex. Amazon")
                with RadioSet(id="specific_partial_op_target_platform"):
                    for button in self.platform_radio_set():
                        yield button

            with Horizontal(id="specific_partial_op_choice_container"):

                yield Label("Available partial operations:")
                with RadioSet(id="specific_partial_op_choice"):
                    yield RadioButton("Quantity", id="quantity")
                    yield RadioButton("Price", id="price")
                    yield RadioButton("Information (Images, Properties, descriptions, all...etc)", id="info")
         
        yield Log()

    def platform_radio_set(self) -> list:
        return [
            RadioButton("Trendyol", id='trendyol'),
            RadioButton("Amazon", id='amazon'),
            RadioButton("HepsiBurada", id='hepsiburada'),
            RadioButton("N11", id='n11'),
            RadioButton("Pazarama", id='pazarama'),
            RadioButton("PTTAVM", id='pttavm'),
            RadioButton("Wordpress", id='wordpress')
        ]

    def hide_containers(self, container_ids: list) -> None:
        for container_id in container_ids:
            self.query_one(f"#{container_id}").display = False

    def show_container(self, container_id: str) -> None:
        self.query_one(f"#{container_id}").display = True

    async def on_button_pressed(self, event: Button.Pressed) -> None:

        if event.button.id == "specific_sku_submit_button":

            self.sku_input = self.query_one("#specific_sku_input", Input).value
            self.sku_value_input = self.query_one("#specific_sku_value_input", Input).value
            
            if self.sku_input:

                # Split and strip both SKU and value inputs
                sku_list = [sku.strip() for sku in self.sku_input.split(",")]
                value_list = [value.strip() for value in self.sku_value_input.split(",")]

                # Pair each SKU with its corresponding value using zip
                if len(value_list) == 1:
                    # Apply the single value to all SKUs
                    self.sku_input = [{sku: value_list[0]} for sku in sku_list]
                else:
                    # Apply corresponding values to each SKU
                    self.sku_input = [{sku: value} for sku, value in zip(sku_list, value_list)]

                self.hide_containers(["specific_sku_op_container"])
                self.show_container("specific_partial_op_choice_container")

    async def on_radio_set_changed(self, event: RadioSet.Changed) -> None:

        if event.radio_set.id == "operation_choice":
            self.hide_containers(["operation_container"])
            if event.pressed.id == "create":
                self.show_container("create_container")
            if event.pressed.id == "update":
                self.show_container("update_container")

        if event.radio_set.id == "create_choice":

            self.hide_containers(["create_container"])

            if event.pressed.id == "auto_copy":

                self.show_container("copy_container")
                self.show_container("copy_source_container")

            if event.pressed.id == "manual_copy":

                self.query_one(Log).write_line(
                    "Enter details manually selected.")

        if event.radio_set.id == "copy_source_platform":

            self.source = event.pressed.id
            self.hide_containers(["copy_source_container"])
            self.show_container("copy_target_container")

        if event.radio_set.id == "copy_target_platform":

            self.target = event.pressed.id
            self.hide_containers(["copy_container"])
            self.show_container("compare_container")

        if event.radio_set.id == "compare_choice":

            if event.pressed.id == "check_exisiting_and_copy":

                self.exit(result={'create': {'source': self.source, 'target': self.target, 'options': "check_existing", 'local_data': True}})

            elif event.pressed.id == "copy_directly":

                self.exit(result={'create': {'source': self.source, 'target': self.target, 'options': "copy_directly", 'local_data': False}})

        if event.radio_set.id == "update_choice":

            self.hide_containers(["update_container"])
            if event.pressed.id == "yes_specific_update":

                self.show_container("specific_update_op_container")

            if event.pressed.id == "no_specific_update":

                self.query_one(Log).write_line(
                    "No specific platform update selected.")
                
                self.exit(result={'update': {'source': None, 'target': None, 'options': None, 'user_input': None}})

        if event.radio_set.id == "specific_update_op_choice":

            if event.pressed.id == "specific_full_update":

                self.query_one(Log).write_line("Full update selected.")
                
                self.exit(result={'update': {'source': self.source, 'target': self.target, 'options': "full"}})

            if event.pressed.id == "specific_partial_update":

                self.hide_containers(["specific_update_op_container"])
                self.show_container("specific_partial_op_source_platform_container")

            if event.pressed.id == "specific_sku_update":

                self.hide_containers(["specific_update_op_container"])

                 # Add an input field for the user to enter SKU or SKU list
                self.show_container("specific_sku_op_container")

        if event.radio_set.id == "specific_partial_op_source_platform":

            self.source = event.pressed.id
            self.hide_containers(["specific_partial_op_source_platform_container"])
            self.show_container("specific_partial_op_target_platform_container")

        if event.radio_set.id == "specific_partial_op_target_platform":

            self.target = event.pressed.id
            self.hide_containers(
                ["specific_partial_op_target_platform_container"])
            self.show_container("specific_partial_op_choice_container")

        if event.radio_set.id == "specific_partial_op_choice":
            if event.pressed.id == "quantity":

                self.query_one(Log).write_line("Partial update for quantity selected.")                
                self.exit(result={'update': {'source': self.source, 'target': self.target, 'options': "quantity", "user_input": self.sku_input}})

            if event.pressed.id == "price":

                self.query_one(Log).write_line("Partial update for price selected.")                
                self.exit(result={'update': {'source': self.source, 'target': self.target, 'options': "price", "user_input": self.sku_input}})

            if event.pressed.id == "info":

                self.query_one(Log).write_line("Partial update for information selected.")                
                self.exit(result={'update': {'source': self.source, 'target': self.target, 'options': "info", "user_input": self.sku_input}})

if __name__ == "__main__":

    app = ProductManagerApp()
    resu = app.run()
    print(resu)
