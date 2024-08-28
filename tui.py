from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal, VerticalScroll
from textual.widgets import Label, RadioSet, RadioButton, Input, Log


class ProductManagerApp(App[str]):

    CSS_PATH = "styles.tcss"
    TITLE = "Product Manager"
    SUB_TITLE = "Product Manager User Interface"



    def on_mount(self) -> None:

        self.source = ''
        self.target = ''
        self.target_options = ''
        self.hide_containers([
            "create_container",
            "copy_container",
            "copy_source_container",
            "copy_target_container",
            "update_container",
            "specific_update_op_container",
            "specific_partial_op_choice_container",
            "storage_container",
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

            with Horizontal(id="storage_container"):

                yield Label("Which storage do you want to use?")
                with RadioSet(id="storage_choice"):
                    yield RadioButton("Online storage", id="online_storage")
                    yield RadioButton("Offline storage", id="offline_storage")

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
                    yield RadioButton("Information (Images, Properties, descriptions)", id="info")

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
            self.show_container("storage_container")

        if event.radio_set.id == "storage_choice":

            if event.pressed.id == "online_storage":

                self.exit(result={'create': {'source': self.source, 'target': self.target, 'options': "copy", 'local_data': False}})

            elif event.pressed.id == "offline_storage":

                self.exit(result={'create': {'source': self.source, 'target': self.target, 'options': None, 'local_data': True}})


        if event.radio_set.id == "update_choice":

            self.hide_containers(["update_container"])
            if event.pressed.id == "yes_specific_update":

                self.show_container("specific_update_op_container")

            if event.pressed.id == "no_specific_update":

                self.query_one(Log).write_line(
                    "No specific platform update selected.")
                
                self.exit(result={'update': {'source': None, 'target': None, 'options': None}})

        if event.radio_set.id == "specific_update_op_choice":

            if event.pressed.id == "specific_full_update":

                self.query_one(Log).write_line("Full update selected.")
                
                self.exit(result={'update': {'source': self.source, 'target': self.target, 'options': "full"}})

            if event.pressed.id == "specific_partial_update":

                self.hide_containers(["specific_update_op_container"])
                self.show_container("specific_partial_op_source_platform_container")

        if event.radio_set.id == "specific_partial_op_source_platform":

            self.source = event.pressed.id
            self.hide_containers(
                ["specific_partial_op_source_platform_container"])
            self.show_container(
                "specific_partial_op_target_platform_container")

        if event.radio_set.id == "specific_partial_op_target_platform":

            self.target = event.pressed.id
            self.hide_containers(
                ["specific_partial_op_target_platform_container"])
            self.show_container("specific_partial_op_choice_container")

        if event.radio_set.id == "specific_partial_op_choice":
            if event.pressed.id == "quantity":

                self.query_one(Log).write_line(
                    "Partial update for quantity selected.")
                
                self.exit(result={'update': {'source': self.source, 'target': self.target, 'options': "qty"}})

            if event.pressed.id == "price":

                self.query_one(Log).write_line(
                    "Partial update for price selected.")
                
                self.exit(result={'update': {'source': self.source, 'target': self.target, 'options': "price"}})


            if event.pressed.id == "info":

                self.query_one(Log).write_line(
                    "Partial update for information selected.")
                
                self.exit(result={'update': {'source': self.source, 'target': self.target, 'options': "info"}})


if __name__ == "__main__":

    app = ProductManagerApp()
    resu = app.run()
    print(resu)
