# Mapping algorithm based on the accumulated configuration bits of the LUTs before a FF.
# It also uses the basic inputs and outputs mapping algorithm for the implemented and reversed netlists.
# WARNING: Both netlists must have the exact same inputs and outputs!
# WARNING: The LUT reduction algorithm only works for LUTs with 2 inputs or more, where I0 and I1 are not constants!
# WARNING: This algorithm cannot iterate through Muxes yet!!!
# WARNING: When SpyDrNet grabs the name of the Flipflop it has a \ as the first character!
# WARNING: Max number of Inputs to a LUT must be 6!
# WARNING: All terms in the list returned from the qm library may not be essential prime implicants! Now they are all Prime Implicants!

from re import A
import spydrnet as sdn
import argparse
from enum import Enum
import math
from qm import qm
from structural_mapping import map_carries_and_flipflops
from timeit import default_timer as timer


class Parameter(Enum):
    BIT_NUM = 0
    CONF_BITS = 1


class State(Enum):
    INIT = 0
    GET_BIT_NUM = 1
    GET_CONF_BITS = 2


# Data Structure for the Configuration Bits Binary Search Tree
class Node:
    def __init__(self):
        self.value = None
        self.children = None


class Flipflop_Data:
    def __init__(self, flipflop_name, configuration_bits, sop):
        self.flipflop_name = flipflop_name
        self.configuration_bits = configuration_bits
        self.sop = sop

    def set_flipflop_name(self, flipflop_name):
        self.flipflop_name = flipflop_name

    def add_configuration_bits(self, configuration_bits):
        self.configuration_bits.append(configuration_bits)

    def set_sop(self, sop):
        self.sop = sop


class Product:
    def __init__(self, string, lut_inputs, lut_inputs_num, negated_inputs_num, state):
        self.string = string
        self.lut_inputs = lut_inputs # List of Input_SOP objects
        self.lut_inputs_num = lut_inputs_num
        self.negated_inputs_num = negated_inputs_num
        self.state = state


class Input_SOP:
    def __init__(self, input, sop, state):
        self.input = input
        self.sop = sop # List of Product objects
        self.state = state


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


def parse_instance_parameters(parameters):
    parameters_data = []

    number_of_bits = ""
    configuration_bits = ""

    current_state = State.INIT
    next_state = State.INIT

    # Parsing Instance Parameters
    for i in range(len(parameters)):
        current_state = next_state

        # SM for Transitions and Actions
        if current_state == State.INIT:
            if parameters[i] == '"':
                next_state = State.GET_BIT_NUM
            elif parameters[i] == "h":
                next_state = State.GET_CONF_BITS

        elif current_state == State.GET_BIT_NUM:
            if parameters[i] == "}" or parameters[i] == "'":
                next_state = State.INIT
            else:
                number_of_bits = number_of_bits + parameters[i]

        elif current_state == State.GET_CONF_BITS:
            if parameters[i] == '"':
                next_state = State.INIT
            else:
                configuration_bits = configuration_bits + parameters[i]

    parameters_data.append(number_of_bits)
    parameters_data.append(configuration_bits)

    return parameters_data


def add_children(parent_node):
    child_1 = Node()
    child_2 = Node()
    new_children = [child_1, child_2]
    parent_node.children = new_children
    return parent_node


def create_tree(new_node, generations, conf_bits_index, conf_bits):
    new_node = add_children(new_node)
    # Generation 1: Return the parent node with values on children
    if generations == 1:
        for child in new_node.children:
            child.value = conf_bits[conf_bits_index]
            conf_bits_index += 1
        return new_node, conf_bits_index
    # Generations 2 or Higher: Return parent node connected with children
    if generations > 1:
        for child in new_node.children:
            child, conf_bits_index = create_tree(
                child, generations - 1, conf_bits_index, conf_bits
            )
        return new_node, conf_bits_index


def get_filtered_values(node, generations, LUT_Inputs, filtered_bst_values):
    # Getting the index of the inputs to the LUT from the generations
    inputs_index = generations - 1
    # Generation 1: Append the children values
    if generations == 1:
        if LUT_Inputs[inputs_index] == "\<constb> ":
            filtered_bst_values.append(node.children[1].value)
        else:
            filtered_bst_values.append(node.children[0].value)
            filtered_bst_values.append(node.children[1].value)
        return filtered_bst_values

    # Generations 2 or Higher: Keep iterating through tree
    if generations > 1:
        if LUT_Inputs[inputs_index] == "\<constb> ":
            filtered_bst_values = get_filtered_values(
                node.children[1], generations - 1, LUT_Inputs, filtered_bst_values
            )
        else:
            filtered_bst_values = get_filtered_values(
                node.children[0], generations - 1, LUT_Inputs, filtered_bst_values
            )
            filtered_bst_values = get_filtered_values(
                node.children[1], generations - 1, LUT_Inputs, filtered_bst_values
            )
        return filtered_bst_values


# For each hex char that it gets, it adds 4 binary numbers to the list
def hex_to_bin(conf_bits):
    new_list = []
    # Transforming each hex conf_bit to a bin
    for char in conf_bits:
        if char == "0":
            new_list.extend(["0", "0", "0", "0"])
        if char == "1":
            new_list.extend(["0", "0", "0", "1"])
        if char == "2":
            new_list.extend(["0", "0", "1", "0"])
        if char == "3":
            new_list.extend(["0", "0", "1", "1"])
        if char == "4":
            new_list.extend(["0", "1", "0", "0"])
        if char == "5":
            new_list.extend(["0", "1", "0", "1"])
        if char == "6":
            new_list.extend(["0", "1", "1", "0"])
        if char == "7":
            new_list.extend(["0", "1", "1", "1"])
        if char == "8":
            new_list.extend(["1", "0", "0", "0"])
        if char == "9":
            new_list.extend(["1", "0", "0", "1"])
        if char == "a":
            new_list.extend(["1", "0", "1", "0"])
        if char == "b":
            new_list.extend(["1", "0", "1", "1"])
        if char == "c":
            new_list.extend(["1", "1", "0", "0"])
        if char == "d":
            new_list.extend(["1", "1", "0", "1"])
        if char == "e":
            new_list.extend(["1", "1", "1", "0"])
        if char == "f":
            new_list.extend(["1", "1", "1", "1"])

    return new_list


# For 4 bin chars, it returns a hex char
def bin_to_hex(conf_bits):
    new_list = []
    # Iterate through all the binary lists
    i = 0
    bin_num = ""
    for bin_char in conf_bits:
        bin_num += bin_char
        # Select the hex character to append to the new list
        if bin_num == "0000":
            new_list.append("0")
        if bin_num == "0001":
            new_list.append("1")
        if bin_num == "0010":
            new_list.append("2")
        if bin_num == "0011":
            new_list.append("3")
        if bin_num == "0100":
            new_list.append("4")
        if bin_num == "0101":
            new_list.append("5")
        if bin_num == "0110":
            new_list.append("6")
        if bin_num == "0111":
            new_list.append("7")
        if bin_num == "1000":
            new_list.append("8")
        if bin_num == "1001":
            new_list.append("9")
        if bin_num == "1010":
            new_list.append("a")
        if bin_num == "1011":
            new_list.append("b")
        if bin_num == "1100":
            new_list.append("c")
        if bin_num == "1101":
            new_list.append("d")
        if bin_num == "1110":
            new_list.append("e")
        if bin_num == "1111":
            new_list.append("f")

        if i == 3:
            i = 0
            bin_num = ""
        else:
            i += 1

    return new_list


def get_reversed_bin_for_each_hex(conf_bits):
    new_list = []
    # Transforming each hex conf_bit to a bin
    for char in conf_bits:
        if char == "0":
            new_list.extend(["0", "0", "0", "0"])
        if char == "1":
            new_list.extend(["1", "0", "0", "0"])
        if char == "2":
            new_list.extend(["0", "1", "0", "0"])
        if char == "3":
            new_list.extend(["1", "1", "0", "0"])
        if char == "4":
            new_list.extend(["0", "0", "1", "0"])
        if char == "5":
            new_list.extend(["1", "0", "1", "0"])
        if char == "6":
            new_list.extend(["0", "1", "1", "0"])
        if char == "7":
            new_list.extend(["1", "1", "1", "0"])
        if char == "8":
            new_list.extend(["0", "0", "0", "1"])
        if char == "9":
            new_list.extend(["1", "0", "0", "1"])
        if char == "a":
            new_list.extend(["0", "1", "0", "1"])
        if char == "b":
            new_list.extend(["1", "1", "0", "1"])
        if char == "c":
            new_list.extend(["0", "0", "1", "1"])
        if char == "d":
            new_list.extend(["1", "0", "1", "1"])
        if char == "e":
            new_list.extend(["0", "1", "1", "1"])
        if char == "f":
            new_list.extend(["1", "1", "1", "1"])

    return new_list


def get_reduced_lut_conf_bits(conf_bits_num, conf_bits, lut_inputs):
    # Getting the reversed configuration bits for the correct reduction of the LUT!
    # This helps the mapping between the conf bits and the LUT inputs
    reversed_conf_bits = []
    for i in reversed(range(len(conf_bits))):
        reversed_conf_bits.append(conf_bits[i])

    lut_conf_bits = get_reversed_bin_for_each_hex(reversed_conf_bits)

    # Build Binary Search Tree based on the lut_conf_bits binary number
    root = Node()
    conf_bits_index = 0
    generations = int(math.log(conf_bits_num, 2))
    root, conf_bits_index = create_tree(
        root, generations, conf_bits_index, lut_conf_bits
    )

    # Getting values of the BST when some of the Inputs to the LUT are \<constb> (1'b1)
    filtered_bst_values = []
    filtered_bst_values = get_filtered_values(
        root, generations, lut_inputs, filtered_bst_values
    )

    # Getting the final conf bits following the Vivado format
    lut_conf_bits = bin_to_hex(
        get_reversed_bin_for_each_hex(bin_to_hex(filtered_bst_values))
    )
    final_conf_bits = []
    for i in reversed(range(len(lut_conf_bits))):
        final_conf_bits.append(lut_conf_bits[i])

    return final_conf_bits


def get_smaller_lut(lut_conf_bits_num, lut_conf_bits, lut_inputs):
    new_conf_bits = ""
    new_lut_inputs = []
    # Get new conf bits
    for i in range(8, 16):
        new_conf_bits = new_conf_bits + lut_conf_bits[i]
    # Get new lut inputs
    for i in range(len(lut_inputs) - 1):
        new_lut_inputs.append(lut_inputs[i])
    return "32", new_conf_bits, new_lut_inputs


def lut_conf_bits_to_lower_case(lut_conf_bits):
    new_conf_bits = ""
    # Put all conf bits in lower case
    for num in lut_conf_bits:
        if num == "A":
            new_conf_bits += "a"
        elif num == "B":
            new_conf_bits += "b"
        elif num == "C":
            new_conf_bits += "c"
        elif num == "D":
            new_conf_bits += "d"
        elif num == "E":
            new_conf_bits += "e"
        elif num == "F":
            new_conf_bits += "f"
        else:
            new_conf_bits += num

    return new_conf_bits


def get_reduced_inputs_sops(inputs_sops, constant_inputs):
    new_inputs_sops = []
    new_input_index = 0

    for input_sop in inputs_sops:
        is_constant = False
        for input in constant_inputs:
            if input_sop.input == input:
                is_constant = True
        if not(is_constant):
            new_input_sop = Input_SOP("I" + str(new_input_index), input_sop.sop, input_sop.state)
            new_inputs_sops.append(new_input_sop)
            new_input_index += 1

    return new_inputs_sops


def get_minterms(conf_bits):
    # Convert configuration bits to binary
    bin_conf_bits = hex_to_bin(conf_bits)
    #print(bin_conf_bits)
    # Loop through the bits in reverse order to grab the correct index of the minterm
    minterms = []
    zeroes = []
    min_index = 0
    for i in reversed(range(len(bin_conf_bits))):
        if bin_conf_bits[i] == '1':
            minterms.append(min_index)
        elif bin_conf_bits[i] == '0':
            zeroes.append(min_index)
        min_index += 1
    #print(minterms)
    #print(zeroes)
    return minterms, zeroes


def get_product(implicant):
    string = implicant
    lut_input_index = len(implicant) - 1
    lut_inputs = []
    negated_num = 0

    for char in implicant:
        if char == 'X':
            pass
        else:
            if char == '0':
                negated_num += 1
            input_sop = Input_SOP('I' + str(lut_input_index), None, "not_found")
            lut_inputs.append(input_sop)
        lut_input_index -= 1
    lut_inputs_number = len(lut_inputs)

    product = Product(string, lut_inputs, lut_inputs_number, negated_num, "not_found")

    return product


def get_sop(prime_implicants):
    sop = []

    for implicant in prime_implicants:
        product = get_product(implicant)
        sop.append(product)

    return sop


def get_lut_data(instance, configuration_bits, previous_luts, smaller_lut):
    previous_luts.append(instance.name)
    lut_inputs = []
    # Initialize the Inputs' SOPs (Max # of inputs is 6!)
    inputs_sops = []
    for i in range(6):
        input_sop = Input_SOP("I" + str(i), None, "not_found")
        inputs_sops.append(input_sop)
    # Check if the LUT is connected in its inputs to any other LUTs to add their Configuration Bits
    # Loop through the pins of the LUT
    for lut_pin in instance.pins:
        # If the pin is an Input
        port_name = lut_pin.inner_pin.port.name
        if "I" in port_name:
            # Check for the wire
            if lut_pin.wire != None:
                # Save the wire name for possible LUT reduction
                lut_inputs.append(str(lut_pin.wire.cable.name))
                # Loop through the pins connected to the wire connected to the LUT
                for out_pin in lut_pin.wire.pins:
                    # Check that it is the outer pin of an instance
                    if "O" in out_pin.inner_pin.port.name:
                        # Check if it is a smaller LUT inside
                        new_smaller_lut = False
                        if "O5" in out_pin.inner_pin.port.name:
                            new_smaller_lut = True
                        # If a LUT is connected to this LUT
                        if "LUT" in out_pin.instance.reference.name:
                            # Check that it is not a previous LUT to get data from it
                            new_lut = True
                            # Loop through the previous luts
                            for i in range(len(previous_luts)):
                                # If found, not new
                                if out_pin.instance.name == previous_luts[i]:
                                    new_lut = False
                            # If new, then get data from it
                            if new_lut:
                                sop, configuration_bits, previous_luts = get_lut_data(
                                    out_pin.instance,
                                    configuration_bits,
                                    previous_luts,
                                    new_smaller_lut,
                                )
                                # Connect the sop to the correct input_sop
                                for input_sop in inputs_sops:
                                    if input_sop.input == port_name:
                                        input_sop.sop = sop

    # Getting the LUT's Number of and the actual Configuration Bits
    parameters_data = []
    if "VERILOG.Parameters" in instance.data:
        parameters = str(instance.data["VERILOG.Parameters"])
        parameters_data = parse_instance_parameters(parameters)

    lut_conf_bits_num = parameters_data[Parameter.BIT_NUM.value]
    lut_conf_bits = parameters_data[Parameter.CONF_BITS.value]
    #print("Initial Configuration Bits:")
    #print(lut_conf_bits)

    # Put all conf bits in lower case
    lut_conf_bits = lut_conf_bits_to_lower_case(lut_conf_bits)

    # If it is a smaller LUT, get it from the LUT6_2
    if smaller_lut:
        lut_conf_bits_num, lut_conf_bits, lut_inputs = get_smaller_lut(
            lut_conf_bits_num, lut_conf_bits, lut_inputs
        )

    # Check if any of the LUT's inputs is a constant 1 to reduce the LUT
    needs_reduction = False
    constant_inputs = []
    for i, value in enumerate(lut_inputs):
        if str(value) == "\<constb> ":
            needs_reduction = True
            constant_inputs.append("I" + str(i))

    #print("Constant Inputs")
    #print(constant_inputs)

    # LUT Reduction
    if needs_reduction and (len(constant_inputs) < 5):
        lut_conf_bits = get_reduced_lut_conf_bits(
            int(lut_conf_bits_num), lut_conf_bits, lut_inputs
        )
        inputs_sops = get_reduced_inputs_sops(inputs_sops, constant_inputs)

    # Add the LUT's configuration bits to the list
    for i in range(len(lut_conf_bits)):
        # Adding each conf bit as a char to the conf bits list
        configuration_bits.append(lut_conf_bits[i])

    # Build SOP Data Structure based on the configuration bits
    minterms, zeroes = get_minterms(lut_conf_bits)
    start = timer()
    #print("minterms again:")
    #print(minterms)
    #print("zeroes again:")
    #print(zeroes)
    prime_implicants = qm(ones = minterms, zeros = zeroes)
    dt = timer() - start
    #print("qm: %f sec" % dt)
    #print(prime_implicants)

    sop = get_sop(prime_implicants)
    #print(sop)

    # Connect the LUT's SOP with its Inputs' SOPs
    for product in sop:
        for input_sop_1 in product.lut_inputs:
            for input_sop_2 in inputs_sops:
                if input_sop_1.input == input_sop_2.input:
                    input_sop_1.sop = input_sop_2.sop

    return sop, configuration_bits, previous_luts


def get_flipflop_data(instance):
    # Check for \ at the beginning of the name to ignore it
    flipflop_name = None
    if instance.name[0] == "\\":
        flipflop_name = instance.name[1:]
    else:
        flipflop_name = instance.name
    configuration_bits = []
    previous_luts = []
    sop = []
    # Loop through the pins of the FF
    for ff_pin in instance.pins:
        # If it is the Input pin on port 'D'
        if ff_pin.inner_pin.port.name == "D":
            # Check for the wire
            if ff_pin.wire != None:
                # Loop through the pins connected to the wire connected to 'D' in the FF
                for out_pin in ff_pin.wire.pins:
                    # If a LUT is connected to the FF
                    if "LUT" in out_pin.instance.reference.name:
                        # Check if it is a smaller LUT inside
                        new_smaller_lut = False
                        if "O5" in out_pin.inner_pin.port.name:
                            new_smaller_lut = True
                        sop, configuration_bits, previous_luts = get_lut_data(
                            out_pin.instance,
                            configuration_bits,
                            previous_luts,
                            new_smaller_lut,
                        )
    flipflop_data = Flipflop_Data(flipflop_name, configuration_bits, sop)
    #print(flipflop_name)
    #print(configuration_bits)
    #print(previous_luts)
    #print(" ")
    return flipflop_data


def get_flipflops_and_configuration_bits(library, carry_mapped_flipflops, impl): 
    netlist_flipflops_data = []
    # Loop through each instance in the current library
    for instance in library.get_instances():
        instance_type = instance.reference.name
        # If the instance is a FF
        if instance_type == "FDSE" or instance_type == "FDRE":
            # Try to find this flipflop in the carry mapped flipflops
            flipflop_already_mapped = False
            for mapped_pair in carry_mapped_flipflops:
                # Compare the flipflop name to the impl FF
                flipflop_name = ""
                if impl:
                    flipflop_name = mapped_pair[0]
                else:
                    flipflop_name = mapped_pair[1]
                if flipflop_name == instance.name:
                    flipflop_already_mapped = True
            if not(flipflop_already_mapped):
                # Get data from it and append it to list
                #print("\\\\\\\\\\\\\\\\\\\\\\\\\\\\ " + instance.name + " \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\")
                flipflop_data = get_flipflop_data(instance)
                netlist_flipflops_data.append(flipflop_data)
    # Return the flipflops names and their lists of configuration bits object
    return netlist_flipflops_data


def make_configuration_bits_list_to_compare(conf_bits):
    list = []

    for num in conf_bits:
        pair = []
        pair.append(num)
        pair.append("not_found")
        list.append(pair)

    return list


def conf_bits_match(list_1, list_2):

    for pair_1 in list_1:
        for pair_2 in list_2:
            if (
                (pair_1[0] == pair_2[0])
                and (pair_1[1] == "not_found")
                and (pair_2[1] == "not_found")
            ):
                pair_1[1] = "found"
                pair_2[1] = "found"

    for pair_1 in list_1:
        if pair_1[1] == "not_found":
            return False

    for pair_2 in list_2:
        if pair_2[1] == "not_found":
            return False

    return True


def map_flipflops_based_on_conf_bits(flipflops_data_1, flipflops_data_2):
    mapped_flipflops = []
    # Loop through each pair in the mapped FFs data_1
    for data_1 in flipflops_data_1:
        conf_bits_1 = make_configuration_bits_list_to_compare(data_1.configuration_bits)
        # Loop through each pair in the mapped FFs data_2
        for data_2 in flipflops_data_2:
            conf_bits_2 = make_configuration_bits_list_to_compare(
                data_2.configuration_bits
            )
            # Check if they match
            if conf_bits_match(conf_bits_1, conf_bits_2):
                mapped_flipflops.append([data_1.flipflop_name, data_2.flipflop_name])

    return mapped_flipflops


def restore_sop_to_not_found_state(sop):
    for product in sop:
        product.state = "not_found"
        for input_sop in product.lut_inputs:
            input_sop.state = "not_found"
            if (input_sop.sop != None):
                restore_sop_to_not_found_state(input_sop.sop)


def restore_product_inputs(product_1, product_2):
    # Restore original "not_found" state for each input_sop in the products
    for input_sop_1 in product_1.lut_inputs:
        input_sop_1.state = "not_found"
        if input_sop_1.sop != None:
            restore_sop_to_not_found_state(input_sop_1.sop)

    for input_sop_2 in product_2.lut_inputs:
        input_sop_2.state = "not_found"
        if input_sop_2.sop != None:
            restore_sop_to_not_found_state(input_sop_2.sop)


def sop_match(sop_1, sop_2):
    sop_1_len = len(sop_1)
    sop_2_len = len(sop_2)
    # Check if they have the same number of products
    if (sop_1_len == sop_2_len):
        products_found = 0
        # Loop through their products
        for product_1 in sop_1:
            #print("P_1")
            #print(product_1)
            for product_2 in sop_2:
                #print("P_2")
                #print(product_2)
                # Check if products match in Inputs Number and Negated Inputs
                if (
                    (product_1.lut_inputs_num == product_2.lut_inputs_num)
                    and (product_1.negated_inputs_num == product_2.negated_inputs_num)
                    and (product_1.state == "not_found")
                    and (product_2.state == "not_found")
                ):
                    # Check that the SOPs in their inputs also match!!!!!!!!!!!!!!!!!!!!!!!!!
                    # Reset counter for matching SOPs
                    matching_input_sops_counter = 0
                    # Loop through the LUT Inputs for sop_1
                    for input_sop_1 in product_1.lut_inputs:
                        # Loop throguh the LUT Inputs for sop_2
                        for input_sop_2 in product_2.lut_inputs:
                            # Check that both Input SOPs have not been mapped
                            if ((input_sop_1.state == "not_found") and (input_sop_2.state == "not_found")):
                                # Check if both don't have a SOP or if their SOPs match
                                if ((input_sop_1.sop == None) and (input_sop_2.sop == None)):
                                    # Update matching status for both SOPs
                                    input_sop_1.state = "found"
                                    input_sop_2.state = "found"
                                    # Increase number of counter for matching SOPs
                                    matching_input_sops_counter += 1
                                elif ((input_sop_1.sop != None) and (input_sop_2.sop != None)):
                                    if (sop_match(input_sop_1.sop, input_sop_2.sop)):
                                        # Update matching status for both SOPs
                                        input_sop_1.state = "found"
                                        input_sop_2.state = "found"
                                        # Increase number of counter for matching SOPs
                                        matching_input_sops_counter += 1
                    # Check if all inputs in the product matched
                    if (matching_input_sops_counter == product_1.lut_inputs_num):
                        # Then map this products (Say that they are found!) 
                        product_1.state = "found"
                        product_2.state = "found"
                        products_found += 1
                        restore_product_inputs(product_1, product_2)
                    else:
                        restore_product_inputs(product_1, product_2)

        #print("Found " + str(products_found) + " out of " + str(sop_1_len))

        # Check that the number of products matches the number of products found
        if (products_found == sop_1_len):
            # Restore Original not_found values for each product
            restore_sop_to_not_found_state(sop_1)
            restore_sop_to_not_found_state(sop_2)

            return True
        else:
            # Restore Original not_found values for each product
            restore_sop_to_not_found_state(sop_1)
            restore_sop_to_not_found_state(sop_2)

            return False
    else:
        return False


def map_flipflops_based_on_logic_functions(flipflops_data_1, flipflops_data_2):
    mapped_flipflops = []

    for data_1 in flipflops_data_1:
        for data_2 in flipflops_data_2:
            #print('\n')
            #print("SOP to compare")
            #print(data_1.sop)
            #print(data_2.sop)
            if sop_match(data_1.sop, data_2.sop):
                #print("MADE IT!!!!!!!!!!!!")
                mapped_flipflops.append([data_1.flipflop_name, data_2.flipflop_name])

    return mapped_flipflops


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


def main():
    ################ Parsing command line arguments ################
    parser = argparse.ArgumentParser()
    parser.add_argument("golden_netlist")
    parser.add_argument("reversed_netlist")
    args = parser.parse_args()

    # Loads the first netlist as intermediate representation (ir1)
    ir1 = sdn.parse(args.golden_netlist)
    # Get the first library in the netlist
    library1 = ir1.libraries[0]

    # Loads the second netlist as intermediate representation (ir2)
    ir2 = sdn.parse(args.reversed_netlist)
    # Get the second library in the netlist
    library2 = ir2.libraries[0]

    # Get mapped carries and flipflops from the counters
    mapped_carries = []
    carry_mapped_flipflops = []
    mapped_carries, carry_mapped_flipflops = map_carries_and_flipflops(library1, library2)
    #print(mapped_carries)

    # Filling the first flipflops data object
    #print("Golden")
    netlist_flipflops_data_1 = get_flipflops_and_configuration_bits(library1, carry_mapped_flipflops, True) 

    # Filling the second flipflops data object
    #print("Reversed")
    netlist_flipflops_data_2 = get_flipflops_and_configuration_bits(library2, carry_mapped_flipflops, False)

    # Printing Flipflops and Logic Equation's Trees
    #print("Golden")
    #print_data(netlist_flipflops_data_1)
    #print("Reversed")
    #print_data(netlist_flipflops_data_2)

    # Map Netlists based on the flipflops data (flipflop name, configuration bits)
    #mapped_flipflops = map_flipflops_based_on_conf_bits(netlist_flipflops_data_1, netlist_flipflops_data_2)

    # Map Netlists based on the flipflops data (flipflop name, configuration bits, sop)
    
    functionally_mapped_flipflops = map_flipflops_based_on_logic_functions(netlist_flipflops_data_1, netlist_flipflops_data_2)

    # ################ Print the Mapped Points File to be used by Conformal ################
    print_conformal_input_output_points(
        ir1.top_instance,
        ir1.top_instance.reference.name,
        ir2.top_instance.reference.name,
    )

    print_conformal_ff_points(
        carry_mapped_flipflops,
        ir1.top_instance.reference.name,
        ir2.top_instance.reference.name,
    )

    print_conformal_ff_points(
        functionally_mapped_flipflops,
        ir1.top_instance.reference.name,
        ir2.top_instance.reference.name,
    )


if __name__ == "__main__":
    main()
