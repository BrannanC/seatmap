import json
import sys
import xml.etree.ElementTree as ET


class SeatMap:
    def __init__(self, filename):
        self.filename = filename
        self.seatmap = {}
        self.json = None
        try:
            tree = ET.parse(filename)
            self.root = tree.getroot()
            # Register namespaces - added "_" because "ns1" or any ns + number is reserved
            self.ns = {"_" + node[0]: node[1] for _, node in ET.iterparse(
                filename, events=['start-ns'])}
            for key, value in self.ns.items():
                ET.register_namespace(key, value)
            self.parse_xml()
        except FileNotFoundError:
            print("Please provide a valid filename")
            raise

    def parse_xml(self):
        self.seatmap.clear()
        self.json = None
        tag = self.root.tag
        # check which kind of seat availability xml
        if 'Envelope' in tag:
            self.envelope_parse()
        elif 'SeatAvailabilityRS' in tag:
            self.SeatAvailabilityRS_parse()
        else:
            raise TypeError("Unknown XML schema")

    def SeatAvailabilityRS_parse(self):
        cabins = self.root.findall('_:SeatMap/_:Cabin', namespaces=self.ns)
        fees = self.get_RS_fees()
        self.seatmap['flight_info'] = {
            'flight_no': self.root.find('_:DataLists/_:FlightSegmentList/_:FlightSegment/_:MarketingCarrier/_:FlightNumber', namespaces=self.ns).text
        }
        for cabin in cabins:
            layout = "".join(col.attrib['Position']
                             for col in cabin.findall('_:CabinLayout/_:Columns', namespaces=self.ns))

            for row in cabin.findall('_:Row', namespaces=self.ns):
                row_num = row.find('_:Number', namespaces=self.ns).text
                # There doesn't seem to be a reference to a class in this file
                self.seatmap[row_num] = {
                    'class': 'Economy', 'layout': layout, 'seats': []}
                for seat in row.findall('_:Seat', namespaces=self.ns):
                    column = seat.find('_:Column', namespaces=self.ns).text
                    new_seat = {}
                    new_seat['seat_id'] = row_num + column
                    # There doesn't seem to be a reference other seat types like kitchen or lavatory
                    new_seat['seat_type'] = 'Seat'
                    new_seat['class'] = self.seatmap[row_num]['class']

                    # fees - OfferItemRefs seems to be the added price for the seat
                    offer_ref = seat.find(
                        '_:OfferItemRefs', namespaces=self.ns)
                    if offer_ref is not None:
                        new_seat['fee'] = fees[offer_ref.text]

                    refs = {ref.text for ref in seat.findall(
                        '_:SeatDefinitionRef', namespaces=self.ns)}
                    new_seat['available'] = True if 'SD4' in refs else False
                    new_seat['occupied'] = True if 'SD19' in refs else False
                    self.seatmap[row_num]['seats'].append(new_seat)

    def get_RS_fees(self):
        fees = {}
        for offer in self.root.findall('_:ALaCarteOffer/_:ALaCarteOfferItem', namespaces=self.ns):
            details = offer.find(
                '_:UnitPriceDetail/_:TotalAmount/_:SimpleCurrencyPrice', namespaces=self.ns)
            fees[offer.attrib['OfferItemID']] = {
                'price': details.text,
                'currency': details.attrib['Code']
            }
        return fees

    def print_RS_info(self):
        seat_def_table = {}
        seat_def_list = self.root.find(
            '_:DataLists/_:SeatDefinitionList', namespaces=self.ns)
        for el in seat_def_list:
            seat_def_table[el.attrib['SeatDefinitionID']] = el.find(
                '_:Description/_:Text', namespaces=self.ns).text
        print(seat_def_table)

    def envelope_parse(self):
        body = self.root.find(
            '_soapenv:Body', namespaces=self.ns)

        # looks like OTA_AirSeatMapRS designates a OTA schema
        OTA_AirSeatMapRS = body.find(
            '_ns:OTA_AirSeatMapRS', namespaces=self.ns)
        # there might be more than one response? Would that mean multiple flights?
        responses = OTA_AirSeatMapRS.find(
            '_ns:SeatMapResponses', namespaces=self.ns)

        # this is written assuming there's only one response
        for res in responses:
            self.seatmap['flight_info'] = {
                'flight_no': res.find('_ns:FlightSegmentInfo', namespaces=self.ns).attrib['FlightNumber']
            }
            details = res.find('_ns:SeatMapDetails', namespaces=self.ns)
            for cabin in details:
                for row in cabin:
                    row_num = row.attrib['RowNumber']
                    self.seatmap[row_num] = {
                        'class': row.attrib['CabinType'],
                        'layout': cabin.attrib['Layout'],
                        'seats': []
                    }
                    for seat in row.findall('_ns:SeatInfo', namespaces=self.ns):
                        new_seat = {}
                        summary = seat.find('_ns:Summary', namespaces=self.ns)
                        service = seat.find('_ns:Service', namespaces=self.ns)
                        features = seat.findall(
                            '_ns:Features', namespaces=self.ns)

                        new_seat['seat_id'] = summary.attrib['SeatNumber']
                        new_seat['class'] = self.seatmap[row_num]['class']
                        new_seat['available'] = True if summary.attrib['AvailableInd'] == 'true' else False
                        new_seat['occupied'] = True if summary.attrib['OccupiedInd'] == 'true' else False

                        # check for fees
                        if service:
                            fee = service.find('_ns:Fee', namespaces=self.ns)
                            formatted_fee = f"{int(fee.attrib['Amount']) / 10 ** int(fee.attrib['DecimalPlaces']):.2f}"
                            new_seat['fee'] = {'price': formatted_fee,
                                               'currency': fee.attrib['CurrencyCode']}

                        # get seat type
                        if seat.attrib['GalleyInd'] == 'true':
                            new_seat['seat_type'] = 'Kitchen'
                        elif seat.attrib['BulkheadInd'] == ' true':
                            new_seat['seat_type'] = 'Bulkhead'
                        else:
                            new_seat['seat_type'] = 'Seat'

                        for feature in features:
                            if 'extension' in feature.attrib and feature.attrib['extension'] == 'Lavatory':
                                new_seat['seat_type'] = 'Lavatory'

                        self.seatmap[row_num]['seats'].append(new_seat)

    def jsonify(self):
        seatmap_json = json.dumps(self.seatmap)
        self.json = seatmap_json

    def save_json(self):
        if not self.json:
            self.jsonify()

        json_filename = "".join(self.filename.split(".")[:1]) + "_parsed.json"
        with open(json_filename, 'w') as f:
            f.write(self.json)

    def pprint_json(self, ch='seat_id'):
        if not self.json:
            self.jsonify()
        sm = json.loads(self.json)
        m = max(int(k) for k in sm.keys())
        rows = [[] for _ in range(m)]
        for num, row in sm.items():
            for seat in row['seats']:
                rows[int(num) - 1].append(seat[ch])
        for r in rows:
            print(r)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("USAGE: python3 seatmap_parser.py [filename]")
    else:
        filename = sys.argv[1]
        SM = SeatMap(filename)
        SM.save_json()
