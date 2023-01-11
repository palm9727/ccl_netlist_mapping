# Algorithm used to map the flipflops found in a shift register, and its output.
import spydrnet as sdn


def go_to_initial_flipflop(instance):


def get_flipflops_to_map_through_shift_register(library, ffs):
    # Loop through each instance in the library to find a flipflop that has its output connected to another flipflop
    for instance in library.get_instances():
        # Select FF
        if ("FDRE" in instance.reference.name) or ("FDSE" in instance.reference.name):
            # Loop through the pins of the FF
            for pin in instance.pins:
                # Find the pin with the Q port
                if "Q" in pin.inner_pin.port.name:
                    # Check that it has a wire
                    if pin.wire != None:
                        # Loop through the pins connected to the wire
                        ffs_connected = 0
                        for w_pin in pin.wire.pins:
                            # Check for outer pin
                            if (type(w_pin) == sdn.OuterPin):
                                # Count FFs connected to wire
                                if ("FDRE" in w_pin.instance.reference.name) or ("FDSE" in w_pin.instance.reference.name):
                                    ffs_connected += 1
                        # Check if it is connected to more than one FF
                        if ffs_connected > 1:
                            # Go to initial FF to map FFs correctly
                            ffs = go_to_initial_flipflop(instance)

    return ffs


def map_shift_register_and_output_flipflops(library1, library2):
    impl_ffs = []
    reversed_ffs = []

    impl_ffs = get_flipflops_to_map_through_shift_register(
        library1, impl_ffs
    )

    reversed_ffs = get_flipflops_to_map_through_shift_register(
        library2, reversed_ffs
    )

    mapped_flipflops = []
    # Map flipflops gathered from the carries
    if len(impl_ffs) == len(reversed_ffs):
        for i in range(len(impl_ffs)):
            mapped_pair = []
            mapped_pair.append(impl_ffs[i])
            mapped_pair.append(reversed_ffs[i])
            mapped_flipflops.append(mapped_pair)

    return mapped_flipflops