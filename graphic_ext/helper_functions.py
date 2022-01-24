

def complex_to_tuple_rounded(c_number: complex) -> (int, int):

    return round(c_number.real), round(c_number.imag)


def complex_to_tuple(c_number: complex) -> (float, float):
    return c_number.real, c_number.imag


def set_attributes(target_object, parameters: dict):

    for name, value in parameters.items():
        getattr(target_object, name)
        setattr(target_object, name, value)