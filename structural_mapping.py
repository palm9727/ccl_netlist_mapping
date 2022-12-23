# Mapping algorithm that includes: Inputs and Outputs Mapping, Structural Mapping through Carries, and Functional Mapping
# WARNING: Both netlists must have the exact same inputs and outputs!
# WARNING: The carry mapping is only for CARRY4 instances!
# WARNING: IF there is multiple counters with the same number of FFs, the mapping might be wrong!
# WARNING: Accessing the wires and pins from the S port of the CARRIES assuming that they go from index 0 to 3!
# WARNING: If a LUT is connected to the carry, the algorithm will grab any FF connected to that LUT!
# WARNING: Algorithm assumes that there is only one CARRY chain in each netlist!
# WARNING: When mapping the nets between carries and flipflops it is assumed that their nets are accessed in the same order.


from operator import truediv
from unicodedata import name
import spydrnet as sdn
import argparse


class Instance:
    def __init__(
        self,
        instance_name,
        instance_type,
        input_wires_names,
        input_wires_number,
        input_wires_matching_number,
        output_wires_names,
        output_wires_number,
        output_wires_matching_number,
        other_wires_names,
        other_wires_number,
    ):
        self.instance_name = instance_name
        self.instance_type = instance_type
        self.input_wires_names = input_wires_names
        self.input_wires_number = input_wires_number
        self.input_wires_matching_number = input_wires_matching_number
        self.output_wires_names = output_wires_names
        self.output_wires_number = output_wires_number
        self.output_wires_matching_number = output_wires_matching_number
        self.other_wires_names = other_wires_names
        self.other_wires_number = other_wires_number


###################################################################################################################
# / ///////////////////////////////////////// Inputs and Outputs /////////////////////////////////////////////////#
###################################################################################################################
def print_conformal_inputs_outputs_mapping(
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


###################################################################################################################
# / ////////////////////////////////// Carries and Flipflops Mapping /////////////////////////////////////////////#
###################################################################################################################
def get_flipflops_through_carry(carry, ffs, carries):
    # print(carry.name + "!!!!!!!!!!!!!!!!!!!!!!!!")
    carries.append(carry.name)
    # Loop through all the pins in the carry to add ffs
    for pin in carry.pins:
        # Find the pin with the S port
        if "S" in pin.inner_pin.port.name:
            # Check that it has a wire
            if pin.wire != None:
                # print(pin.wire.cable.name)
                # Loop through the pins connected to the wire
                for wire_pin in pin.wire.pins:
                    # print(wire_pin.instance.reference.name)
                    # Check for FF Output
                    if "Q" in wire_pin.inner_pin.port.name:
                        # Case where a FF is connected directly to the carry!
                        if ("FDRE" in wire_pin.instance.reference.name) or (
                            "FDSE" in wire_pin.instance.reference.name
                        ):
                            # print("IT GETS HERE!!!!!!")
                            # Add ff to the list
                            ffs.append(wire_pin.instance.name)
                            # print(ffs)
                    # Check for LUT Output
                    elif "O" in wire_pin.inner_pin.port.name:
                        # Case where a LUT is connected to the carry!
                        if "LUT" in wire_pin.instance.reference.name:
                            lut = wire_pin.instance
                            # Loop through the pins of the LUT
                            for lut_pin in lut.pins:
                                # Find the pin with the I port
                                if "I" in lut_pin.inner_pin.port.name:
                                    # Check that it has a wire
                                    if lut_pin.wire != None:
                                        # Loop through the pins connected to the lut's wire
                                        for lut_wire_pin in lut_pin.wire.pins:
                                            # Check for FF Output
                                            if "Q" in lut_wire_pin.inner_pin.port.name:
                                                # Case where a FF is connected directly to the LUT!
                                                if (
                                                    "FDRE"
                                                    in lut_wire_pin.instance.reference.name
                                                ) or (
                                                    "FDSE"
                                                    in lut_wire_pin.instance.reference.name
                                                ):
                                                    # Add ff to the list
                                                    ffs.append(
                                                        lut_wire_pin.instance.name
                                                    )
                                                    # print(ffs)
                        # Ignore all other cases!
    # Done with adding flipflops from the carry!
    # Loop through all the pins in the carry to move to the next carry, or to add the final ff
    for pin in carry.pins:
        # Find the pin with the CO port
        if "CO" in pin.inner_pin.port.name:
            # Check that it has a wire
            if pin.wire != None:
                # Move to the next carry!
                # Loop through the pins connected to the wire
                for wire_pin in pin.wire.pins:
                    # Find the wire_pin with the CI port
                    if "CI" in wire_pin.inner_pin.port.name:
                        # Case where the carry is connected directly to the carry!
                        if "CARRY" in wire_pin.instance.reference.name:
                            # Jump to the new carry
                            ffs, carries = get_flipflops_through_carry(
                                wire_pin.instance, ffs, carries
                            )
            # Else this is the last Carry!
    return ffs, carries


def get_flipflops_to_map_through_carries(library, ffs, carries):
    # Loop through each instance in the current library to find the first carry!
    for instance in library.get_instances():
        # Select carry
        if "CARRY" in instance.reference.name:
            # Loop through the pins of the CARRY
            for pin in instance.pins:
                # Find the pin with the CI port
                if "CI" in pin.inner_pin.port.name:
                    # Check that it has a wire
                    if pin.wire != None:
                        # Check if it is connected to a constant (ground); b for reversed, 0 for impl
                        if ("\<constb> " == pin.wire.cable.name) or (
                            "\<const0> " == pin.wire.cable.name
                        ):
                            # Get FFs through carry
                            ffs, carries = get_flipflops_through_carry(
                                instance, ffs, carries
                            )
    return ffs, carries


def print_mapped_carries(mapped_carries):
    for carry_pair in mapped_carries:
        print(carry_pair[0], " <-> ", carry_pair[1])


def print_mapped_flipflops_through_carries(mapped_ffs):
    for ff_pair in mapped_ffs:
        print(ff_pair[0], " <-> ", ff_pair[1])


def map_carries_and_flipflops(library1, library2):
    impl_carries = []
    reversed_carries = []
    impl_ffs = []
    reversed_ffs = []

    impl_ffs, impl_carries = get_flipflops_to_map_through_carries(
        library1, impl_ffs, impl_carries
    )

    reversed_ffs, reversed_carries = get_flipflops_to_map_through_carries(
        library2, reversed_ffs, reversed_carries
    )

    mapped_carries = []
    # Map carry chains
    if len(impl_carries) == len(reversed_carries):
        for i in range(len(impl_carries)):
            mapped_pair = []
            mapped_pair.append(impl_carries[i])
            mapped_pair.append(reversed_carries[i])
            mapped_carries.append(mapped_pair)

    #print_mapped_carries(mapped_carries)

    mapped_flipflops = []
    # Map flipflops gathered from the carries
    if len(impl_ffs) == len(reversed_ffs):
        for i in range(len(impl_ffs)):
            mapped_pair = []
            mapped_pair.append(impl_ffs[i])
            mapped_pair.append(reversed_ffs[i])
            mapped_flipflops.append(mapped_pair)

    # print_mapped_flipflops_through_carries(mapped_flipflops)

    return mapped_carries, mapped_flipflops


###################################################################################################################
# / ////////////////////////////////// Rest of Netlist Structural Mapping ////////////////////////////////////////#
###################################################################################################################
def print_mapped_blocks(mapped_points):
    for mapped_pair in mapped_points:
        print(mapped_pair[0] + " <-> " + mapped_pair[1])


def print_netlist(netlist):
    for instance in netlist:
        if "CARRY" in instance.instance_type:
            print(instance.instance_name)
            print(instance.instance_type)
            print("Inputs")
            print(instance.input_wires_names)
            print(instance.input_wires_number)
            print(instance.input_wires_matching_number)
            print("Outputs")
            print(instance.output_wires_names)
            print(instance.output_wires_number)
            print(instance.output_wires_matching_number)
            print("Others")
            print(instance.other_wires_names)
            print(instance.other_wires_number, "\n")


def get_netlist(library):
    netlist = []
    # Loop through each instance in the current library
    for instance in library.get_instances():
        instance_name = instance.name
        instance_type = instance.reference.name
        input_wires_names = []
        output_wires_names = []
        other_wires_names = []
        # Loop through each of the pins in the instance
        for pin in instance.pins:
            # Check to see that there is a wire connected to the pin
            if pin.wire != None:
                cable_name = pin.wire.cable.name
                wire_index = str(pin.wire.index())
                wire_name = cable_name + "[" + wire_index + "]"
                if ("I" in pin.inner_pin.port.name) or ("S" in pin.inner_pin.port.name):
                    # Added filter for CARRY (CARRIES are mapped through the real netlist)
                    if (
                        ("DI" in pin.inner_pin.port.name)
                        or ("CYINIT" in pin.inner_pin.port.name)
                        or ("CI" in pin.inner_pin.port.name)
                    ):
                        pass
                    else:
                        input_wires_names.append(wire_name)
                elif "D" in pin.inner_pin.port.name:
                    # Added filter for CARRY (CARRIES are mapped through the real netlist)
                    if (
                        ("DI" in pin.inner_pin.port.name)
                        or ("CYINIT" in pin.inner_pin.port.name)
                        or ("CI" in pin.inner_pin.port.name)
                    ):
                        pass
                    else:
                        input_wires_names.append(wire_name)
                elif "O" in pin.inner_pin.port.name:
                    # Check that the wire is connected to other Input Pins
                    if len(pin.wire.pins) > 1:
                        # Check that it is not a CO signal (CARRIES are mapped through the real netlist)
                        if "CO" in pin.inner_pin.port.name:
                            pass
                        else:
                            output_wires_names.append(wire_name)
                elif "Q" in pin.inner_pin.port.name:
                    output_wires_names.append(wire_name)
                else:
                    other_wires_names.append(wire_name)
        # Getting the lengths
        input_wires_number = len(input_wires_names)
        output_wires_number = len(output_wires_names)
        other_wires_number = len(other_wires_names)
        # Setting initial matching numbers
        input_wires_matching_number = 0
        output_wires_matching_number = 0
        # Check if the instance is a LUT for special LUT cases!
        if "LUT" in instance_name:
            # Check if the instance is a LUT with all constant inputs to ignore it!
            number_of_constant_inputs = 0
            for wire_name in input_wires_names:
                if wire_name == "\\<constb> [0]":
                    number_of_constant_inputs += 1
            if number_of_constant_inputs == input_wires_number:
                pass  # Ignore these LUTs!
            else:
                # Check for 2 Output LUT
                if output_wires_number > 1:
                    # Divide LUT5 from LUT6 in the LUT6_2 and perform analysis on each of them !!!
                    #  Getting O5 LUT
                    new_instance_name = instance_name + "_LUT5"
                    new_instance_type = "LUT5"
                    new_input_wires_names = []
                    new_output_wires_names = []
                    # Loop to get the LUT5 inputs
                    i = 0
                    for i in range(0, 6):
                        new_input_wires_names.append(input_wires_names[i])
                    new_input_wires_number = len(new_input_wires_names)
                    # Get the LUT5 output
                    new_output_wires_names.append(output_wires_names[0])
                    new_output_wires_number = len(new_output_wires_names)
                    # Check if the LUT5 has constant inputs to reduce it!
                    number_of_new_constant_inputs = 0
                    for wire_name in new_input_wires_names:
                        if wire_name == "\\<constb> [0]":
                            number_of_new_constant_inputs += 1
                    if number_of_new_constant_inputs > 0:
                        # Reduce the LUT5!
                        reduced_input_wires_names = []
                        for wire_name in new_input_wires_names:
                            if wire_name != "\\<constb> [0]":
                                reduced_input_wires_names.append(wire_name)
                        # Get reduced input wires number
                        reduced_input_wires_number = len(reduced_input_wires_names)
                        # Get reduced instance type
                        reduced_instance_type = "LUT" + str(reduced_input_wires_number)
                        # Get reduced instance name
                        reduced_instance_name = instance_name + reduced_instance_type
                        # Creating reduced instance object
                        reduced_instance = Instance(
                            reduced_instance_name,
                            reduced_instance_type,
                            reduced_input_wires_names,
                            reduced_input_wires_number,
                            input_wires_matching_number,
                            new_output_wires_names,
                            new_output_wires_number,
                            output_wires_matching_number,
                            other_wires_names,
                            other_wires_number,
                        )
                        # Adding instance to the netlist
                        netlist.append(reduced_instance)
                    else:
                        # Add LUT5 to the netlist!
                        # Creating new instance object
                        new_instance = Instance(
                            new_instance_name,
                            new_instance_type,
                            new_input_wires_names,
                            new_input_wires_number,
                            input_wires_matching_number,
                            new_output_wires_names,
                            new_output_wires_number,
                            output_wires_matching_number,
                            other_wires_names,
                            other_wires_number,
                        )
                        # Adding instance to the netlist
                        netlist.append(new_instance)
                    # Continuing with O6 LUT
                    new_instance_type = "LUT6"
                    new_output_wires_names = []
                    # Get the LUT6 output
                    new_output_wires_names.append(output_wires_names[1])
                    new_output_wires_number = len(new_output_wires_names)
                    # Check if the LUT6 has constant inputs in order to reduce it!
                    if number_of_constant_inputs > 0:
                        # Reduce the LUT by creating new instance!
                        # Get new input wires names
                        reduced_input_wires_names = []
                        for wire_name in input_wires_names:
                            if wire_name != "\\<constb> [0]":
                                reduced_input_wires_names.append(wire_name)
                        # Get new input wires number
                        reduced_input_wires_number = len(reduced_input_wires_names)
                        # Get new instance type
                        reduced_instance_type = "LUT" + str(reduced_input_wires_number)
                        # Creating new instance object
                        reduced_instance = Instance(
                            instance_name,
                            reduced_instance_type,
                            reduced_input_wires_names,
                            reduced_input_wires_number,
                            input_wires_matching_number,
                            new_output_wires_names,
                            new_output_wires_number,
                            output_wires_matching_number,
                            other_wires_names,
                            other_wires_number,
                        )
                        # Adding instance to the netlist
                        netlist.append(reduced_instance)
                    else:
                        # Add LUT6 to the netlist!
                        # Creating new instance object
                        new_instance = Instance(
                            instance_name,
                            new_instance_type,
                            input_wires_names,
                            input_wires_number,
                            input_wires_matching_number,
                            new_output_wires_names,
                            new_output_wires_number,
                            output_wires_matching_number,
                            other_wires_names,
                            other_wires_number,
                        )
                        # Adding instance to the netlist
                        netlist.append(new_instance)
                else:
                    # Given that it is a one output LUT
                    # Check if the LUT has constant inputs in order to reduce it!
                    if number_of_constant_inputs > 0:
                        # Reduce the LUT by creating new instance!
                        # Get new input wires names
                        reduced_input_wires_names = []
                        for wire_name in input_wires_names:
                            if wire_name != "\\<constb> [0]":
                                reduced_input_wires_names.append(wire_name)
                        # Get new input wires number
                        reduced_input_wires_number = len(reduced_input_wires_names)
                        # Get new instance type
                        reduced_instance_type = "LUT" + str(reduced_input_wires_number)
                        # Creating new instance object
                        new_instance = Instance(
                            instance_name,
                            reduced_instance_type,
                            reduced_input_wires_names,
                            reduced_input_wires_number,
                            input_wires_matching_number,
                            output_wires_names,
                            output_wires_number,
                            output_wires_matching_number,
                            other_wires_names,
                            other_wires_number,
                        )
                        # Adding instance to the netlist
                        netlist.append(new_instance)
                    else:
                        # Add LUT to the netlist!
                        # Creating new instance object
                        new_instance = Instance(
                            instance_name,
                            instance_type,
                            input_wires_names,
                            input_wires_number,
                            input_wires_matching_number,
                            output_wires_names,
                            output_wires_number,
                            output_wires_matching_number,
                            other_wires_names,
                            other_wires_number,
                        )
                        # Adding instance to the netlist
                        netlist.append(new_instance)
        else:
            # Add instance to the netlist!
            # Creating new instance object
            new_instance = Instance(
                instance_name,
                instance_type,
                input_wires_names,
                input_wires_number,
                input_wires_matching_number,
                output_wires_names,
                output_wires_number,
                output_wires_matching_number,
                other_wires_names,
                other_wires_number,
            )
            # Adding instance to the netlist
            netlist.append(new_instance)

    return netlist


def structurally_map_netlists(
    golden_netlist, reversed_netlist, mapped_points, init_mapped_blocks
):
    ########################## Structural Mapping Algorithm ##########################
    mapped_blocks = init_mapped_blocks
    progress = True
    # Loop until all blocks have been mapped or there is no more progress
    while ((len(reversed_netlist) - 2) != mapped_blocks) and (
        progress
    ):  # - 2 for G and P (Which should stay unmapped for now)
        progress = False
        # Loop through reversed netlist blocks
        for reversed_instance in reversed_netlist:
            # If instance has unmatching wires (Not mapped yet)
            if (
                reversed_instance.input_wires_number
                != reversed_instance.input_wires_matching_number
            ) and (
                reversed_instance.output_wires_number
                != reversed_instance.output_wires_matching_number
            ):
                potential_instances = []
                higher_potential_instances = []
                saved_instance = None
                instances_matching = 0
                # Loop through golden netlist blocks
                for impl_instance in golden_netlist:
                    # If instances have same # of wires as input, output, and other (Are structurally the same)
                    if (
                        (
                            reversed_instance.input_wires_number
                            == impl_instance.input_wires_number
                        )
                        and (
                            reversed_instance.output_wires_number
                            == impl_instance.output_wires_number
                        )
                        and (
                            reversed_instance.other_wires_number
                            == impl_instance.other_wires_number
                        )
                    ):
                        # print(reversed_instance.instance_name + " vs " + impl_instance.instance_name)
                        # Check for matching in inputs
                        input_wires_matching = 0
                        for reversed_wire in reversed_instance.input_wires_names:
                            for impl_wire in impl_instance.input_wires_names:
                                if reversed_wire == impl_wire:
                                    input_wires_matching += 1
                        # Check for matching in outputs
                        output_wires_matching = 0
                        for reversed_wire in reversed_instance.output_wires_names:
                            for impl_wire in impl_instance.output_wires_names:
                                if reversed_wire == impl_wire:
                                    output_wires_matching += 1
                        # If they match, add to potential_instances
                        if (input_wires_matching > 0) or (output_wires_matching > 0):
                            wires_matching = (
                                input_wires_matching + output_wires_matching
                            )
                            potential_pair = [impl_instance, wires_matching]
                            potential_instances.append(potential_pair)
                # Check if it is only one, if not get the ones with highest number of matching wires
                if len(potential_instances) == 1:
                    instances_matching += 1
                    saved_instance = potential_instances[0][0]
                elif len(potential_instances) > 1:
                    # Getting the max number of matching wires
                    max_num = 0
                    for i in range(len(potential_instances)):
                        matching_wires = potential_instances[i][1]
                        if matching_wires > max_num:
                            max_num = matching_wires
                    # Getting the instances with the max number of matching wires
                    for i in range(len(potential_instances)):
                        matching_wires = potential_instances[i][1]
                        if matching_wires == max_num:
                            higher_potential_instances.append(potential_instances[i])
                    # If it is only one save the instance, if not prepare for no mapping!
                    if len(higher_potential_instances) == 1:
                        instances_matching += 1
                        saved_instance = higher_potential_instances[0][0]
                    else:
                        instances_matching += 2
                # ? Actual Mapping!!!
                if instances_matching == 1:
                    # Mapping the nets of the block!
                    maps_performed = 0
                    # Updating the number of matching wires the first time!
                    if (reversed_instance.input_wires_matching_number == 0) and (
                        reversed_instance.output_wires_matching_number == 0
                    ):
                        for reversed_wire in reversed_instance.input_wires_names:
                            for impl_wire in saved_instance.input_wires_names:
                                if reversed_wire == impl_wire:
                                    reversed_instance.input_wires_matching_number += 1
                        for reversed_wire in reversed_instance.output_wires_names:
                            for impl_wire in saved_instance.output_wires_names:
                                if reversed_wire == impl_wire:
                                    reversed_instance.output_wires_matching_number += 1
                        maps_performed += 1
                    # Input Mapping!!!
                    if (
                        reversed_instance.input_wires_number
                        - reversed_instance.input_wires_matching_number
                    ) == 1:
                        # Map Input Net
                        # Find Input wire in the reversed_instance that is not found in the impl_instance
                        reversed_input_index = 0
                        reversed_input_found = False
                        for i, reversed_wire in enumerate(
                            reversed_instance.input_wires_names
                        ):
                            for impl_wire in saved_instance.input_wires_names:
                                if reversed_wire == impl_wire:
                                    reversed_input_found = True
                            if reversed_input_found == False:
                                reversed_input_index = i
                            reversed_input_found = False
                        # Find Input wire in the impl_instance that is not found in the reversed_instance
                        impl_input_index = 0
                        impl_input_found = False
                        for i, impl_wire in enumerate(saved_instance.input_wires_names):
                            for reversed_wire in reversed_instance.input_wires_names:
                                if reversed_wire == impl_wire:
                                    impl_input_found = True
                            if impl_input_found == False:
                                impl_input_index = i
                            impl_input_found = False
                        # Map the input net
                        old_wire_name = reversed_instance.input_wires_names[
                            reversed_input_index
                        ]
                        new_wire_name = saved_instance.input_wires_names[
                            impl_input_index
                        ]
                        reversed_instance.input_wires_names[
                            reversed_input_index
                        ] = new_wire_name
                        reversed_instance.input_wires_matching_number += 1
                        # Loop through all the reversed blocks, and if they have inputs or
                        # outputs equal to the old_wire_name change them to be the new_wire_name
                        for reversed_block in reversed_netlist:
                            for i, reversed_block_input_wire in enumerate(
                                reversed_block.input_wires_names
                            ):
                                if reversed_block_input_wire == old_wire_name:
                                    reversed_block.input_wires_names[i] = new_wire_name
                            for i, reversed_block_output_wire in enumerate(
                                reversed_block.output_wires_names
                            ):
                                if reversed_block_output_wire == old_wire_name:
                                    reversed_block.output_wires_names[i] = new_wire_name
                        maps_performed += 1
                    # Output Mapping!!!
                    if (
                        reversed_instance.output_wires_number
                        - reversed_instance.output_wires_matching_number
                    ) == 1:
                        # Map Output Net
                        # This should work if all blocks in the netlist only have one output wire!
                        for i, reversed_wire in enumerate(
                            reversed_instance.output_wires_names
                        ):
                            for impl_wire in saved_instance.output_wires_names:
                                if reversed_wire != impl_wire:
                                    reversed_instance.output_wires_names[i] = impl_wire
                                    reversed_instance.output_wires_matching_number += 1
                                    # Loop through all the reversed blocks, and if they have inputs
                                    # equal to the reversed_wire change them to be the impl_wire
                                    for reversed_block in reversed_netlist:
                                        for i, reversed_block_input_wire in enumerate(
                                            reversed_block.input_wires_names
                                        ):
                                            if (
                                                reversed_block_input_wire
                                                == reversed_wire
                                            ):
                                                reversed_block.input_wires_names[
                                                    i
                                                ] = impl_wire
                        maps_performed += 1
                    # This is an impotant statement
                    # > 0: The algorithm maps the most similar instances. (They have the same structure and the most matching input and output wires)
                    # > 1: The algorithm only maps the most similar instances that are only missing one output or input.
                    if maps_performed > 1:
                        mapped_blocks += 1
                        progress = True
                        mapped_pair_and_types = []
                        mapped_pair_and_types.append(saved_instance.instance_name)
                        mapped_pair_and_types.append(reversed_instance.instance_name)
                        mapped_pair_and_types.append(saved_instance.instance_type)
                        mapped_pair_and_types.append(reversed_instance.instance_type)
                        mapped_points.append(mapped_pair_and_types)

    # Prints all mapped blocks
    print_mapped_blocks(mapped_points)

    return mapped_points


def update_netlists_from_carries_and_flipflops_mapping(
    mapped_carries, mapped_flipflops, golden_netlist, reversed_netlist
):
    # Update netlist with the mapped carries
    # Loop through the mapped carries
    for mapped_pair in mapped_carries:
        # Loop through the impl_netlist
        for impl_instance in golden_netlist:
            # Find impl_carry
            if mapped_pair[0] == impl_instance.instance_name:
                # print(mapped_pair[0], " with ", impl_instance.instance_name)
                # Loop through the reversed_netlist
                for reversed_instance in reversed_netlist:
                    # Find reversed_carry
                    if mapped_pair[1] == reversed_instance.instance_name:
                        # print(mapped_pair[1], " with ", reversed_instance.instance_name)
                        # Update Inputs in the reversed_carry
                        for i, reversed_wire in enumerate(
                            reversed_instance.input_wires_names
                        ):
                            # Update Input in cell
                            old_wire_name = reversed_wire
                            new_wire_name = impl_instance.input_wires_names[i]
                            reversed_instance.input_wires_names[i] = new_wire_name
                            reversed_instance.input_wires_matching_number += 1
                            # Update wire in netlist
                            for reversed_block in reversed_netlist:
                                # Updating Inputs
                                for i, reversed_block_input_wire in enumerate(
                                    reversed_block.input_wires_names
                                ):
                                    if reversed_block_input_wire == old_wire_name:
                                        reversed_block.input_wires_names[
                                            i
                                        ] = new_wire_name
                                # Updating Outputs
                                for i, reversed_block_output_wire in enumerate(
                                    reversed_block.output_wires_names
                                ):
                                    if reversed_block_output_wire == old_wire_name:
                                        reversed_block.output_wires_names[
                                            i
                                        ] = new_wire_name
                        # Update Outputs in the reversed_carry
                        for i, reversed_wire in enumerate(
                            reversed_instance.output_wires_names
                        ):
                            # Update Output in cell
                            old_wire_name = reversed_wire
                            new_wire_name = impl_instance.output_wires_names[i]
                            reversed_instance.output_wires_names[i] = new_wire_name
                            reversed_instance.output_wires_matching_number += 1
                            # Update wire in netlist
                            for reversed_block in reversed_netlist:
                                # Updating Inputs
                                for i, reversed_block_input_wire in enumerate(
                                    reversed_block.input_wires_names
                                ):
                                    if reversed_block_input_wire == old_wire_name:
                                        reversed_block.input_wires_names[
                                            i
                                        ] = new_wire_name
                        # Update Other wires in the reversed_carry
                        for i, reversed_wire in enumerate(
                            reversed_instance.other_wires_names
                        ):
                            # Update Other wire in cell
                            old_wire_name = reversed_wire
                            new_wire_name = impl_instance.other_wires_names[i]
                            reversed_instance.other_wires_names[i] = new_wire_name
                            # reversed_instance.other_wires_matching_number += 1
                            # Update wire in netlist
                            for reversed_block in reversed_netlist:
                                # Updating Inputs
                                for i, reversed_block_input_wire in enumerate(
                                    reversed_block.input_wires_names
                                ):
                                    if reversed_block_input_wire == old_wire_name:
                                        reversed_block.input_wires_names[
                                            i
                                        ] = new_wire_name
                                # Updating Outputs
                                for i, reversed_block_output_wire in enumerate(
                                    reversed_block.output_wires_names
                                ):
                                    if reversed_block_output_wire == old_wire_name:
                                        reversed_block.output_wires_names[
                                            i
                                        ] = new_wire_name
                                # Updating Other wires
                                for i, reversed_block_other_wire in enumerate(
                                    reversed_block.other_wires_names
                                ):
                                    if reversed_block_other_wire == old_wire_name:
                                        reversed_block.other_wires_names[
                                            i
                                        ] = new_wire_name
                        # Done updating CARRY

    # Update netlist with the mapped flipflops (May not be needed)

    return golden_netlist, reversed_netlist


###################################################################################################################
# / /////////////////////////////////////////// Netlist Mapping///////////////////////////////////////////////////#
###################################################################################################################
def map_netlists(golden_netlist_arg, reversed_netlist_arg):
    # Loads the first netlist as intermediate representation (ir1)
    ir1 = sdn.parse(golden_netlist_arg)
    # Get the first library in the netlist
    library1 = ir1.libraries[0]

    # Loads the second netlist as intermediate representation (ir2)
    ir2 = sdn.parse(reversed_netlist_arg)
    # Get the first library in the netlist
    library2 = ir2.libraries[0]

    # Get netlists for the structural mapping algorithm
    golden_netlist = get_netlist(library1)
    reversed_netlist = get_netlist(library2)

    # Print Data Before Mapping
    # ################ Printing Data from Golden netlist ##################
    # print("///////////////////////////////// golden_netlist ///////////////////////////////////")
    # print_netlist(golden_netlist)
    # ################ Printing Data from Reversed netlist ################
    # print("///////////////////////////////// reversed_netlist /////////////////////////////////")
    # print_netlist(reversed_netlist)

    # Get mapped carries and flipflops from the counters
    mapped_carries = []
    mapped_flipflops = []
    mapped_carries, mapped_flipflops = map_carries_and_flipflops(library1, library2)

    (
        golden_netlist,
        reversed_netlist,
    ) = update_netlists_from_carries_and_flipflops_mapping(
        mapped_carries, mapped_flipflops, golden_netlist, reversed_netlist
    )

    # Structurally map the rest of the netlists
    mapped_blocks = len(mapped_carries) + len(mapped_flipflops)
    mapped_points = []
    mapped_points = structurally_map_netlists(
        golden_netlist, reversed_netlist, mapped_points, mapped_blocks
    )

    # Print Data After Mapping
    # ################ Printing Data from Golden netlist ##################
    # print("///////////////////////////////// golden_netlist ///////////////////////////////////")
    # print_netlist(golden_netlist)
    # ################ Printing Data from Reversed netlist ################
    # print("///////////////////////////////// reversed_netlist /////////////////////////////////")
    # print_netlist(reversed_netlist)

    # ################################# Print the Mapped Points File to be used by Conformal ###################################
    # print_conformal_inputs_outputs_mapping(ir1.top_instance, ir1.top_instance.reference.name, ir2.top_instance.reference.name)


def main():
    ################ Parsing command line arguments ################
    parser = argparse.ArgumentParser()
    parser.add_argument("golden_netlist")
    parser.add_argument("reversed_netlist")
    args = parser.parse_args()
    map_netlists(args.golden_netlist, args.reversed_netlist)


if __name__ == "__main__":
    main()
