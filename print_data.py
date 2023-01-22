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
    mapped_flipflops, golden_module_name, reversed_module_name, printing_structural
):
    for ff_names in mapped_flipflops:
        if (printing_structural):
            impl_ff_name = ff_names[0][1:]
            reversed_ff_name = ff_names[1]
            print(
                "add mapped points "
                + impl_ff_name
                + " "
                + reversed_ff_name
                + " -type DFF DFF -module "
                + golden_module_name
                + " "
                + reversed_module_name
            )
        else:
            impl_ff_name = ff_names[0]
            reversed_ff_name = ff_names[1]
            print(
                "add mapped points "
                + impl_ff_name
                + " "
                + reversed_ff_name
                + " -type DFF DFF -module "
                + golden_module_name
                + " "
                + reversed_module_name
            )
        


def print_sop(sop, level):
    # Prepare identation based on the level
    tabs = ""
    for i in range(level):
        tabs += "\t"
    print(tabs + "SOP:")
    # Loop through the products
    for product in sop:
        print(tabs + '(' + str(product.lut_inputs_num) + ", " + str(product.negated_inputs_num) + ')')
        # Loop through the inputs
        for lut_input in product.lut_inputs:
            print(tabs + "\t" + lut_input.input)
            if lut_input.sop != None:
                level += 1
                level = print_sop(lut_input.sop, level)
            else:
                print(tabs + "\t" + "-")
    level -= 1
    return level 


def print_data(data):
    # Loop through the flipflop data list
    for flipflop_data in data:
        print(flipflop_data.flipflop_name)
        level = 1
        level = print_sop(flipflop_data.sop, level)
        print("\n")
    pass