def print_conformal_input_output_points(
    top_instance, golden_module_name, reversed_module_name
):
    # Loop through each of the ports in the instance
    for top_port in top_instance.get_ports():
        if "IN" in str(top_port.direction):
            if len(top_port.pins) > 1:
                for pin in top_port.pins:
                    if pin.wire != None:
                        input_name = (
                            pin.wire.cable.name + "[" + str(pin.wire.index()) + "]"
                        )
                        print(
                            "add mapped points "
                            + input_name
                            + " "
                            + input_name
                            + " -type PI PI -module "
                            + golden_module_name
                            + " "
                            + reversed_module_name
                        )
            else:
                print(
                    "add mapped points "
                    + top_port.name
                    + " "
                    + top_port.name
                    + " -type PI PI -module "
                    + golden_module_name
                    + " "
                    + reversed_module_name
                )
        elif "OUT" in str(top_port.direction):
            if len(top_port.pins) > 1:
                for pin in top_port.pins:
                    if pin.wire != None:
                        input_name = (
                            pin.wire.cable.name + "[" + str(pin.wire.index()) + "]"
                        )
                        print(
                            "add mapped points "
                            + input_name
                            + " "
                            + input_name
                            + " -type PO PO -module "
                            + golden_module_name
                            + " "
                            + reversed_module_name
                        )
            else:
                print(
                    "add mapped points "
                    + top_port.name
                    + " "
                    + top_port.name
                    + " -type PO PO -module "
                    + golden_module_name
                    + " "
                    + reversed_module_name
                )
        else:
            print("Unable to recognize port of the top module!")

def print_conformal_ff_points(
    mapped_flipflops, golden_module_name, reversed_module_name
):
    for ff_names in mapped_flipflops:
        print(
            "add mapped points "
            + ff_names[0]
            + " "
            + ff_names[1]
            + " -type DFF DFF -module "
            + golden_module_name
            + " "
            + reversed_module_name
        )