import win32print

def get_printer_list():
    printer_list = []
    printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL, None, 1)
    for printer in printers:
        printer_list.append(printer[2])
    return printer_list

printer_list = get_printer_list()
print("Connected printers:", printer_list)