def get_currency(key=None, value=None):
    currency = {
        10000: 'AED',
        10001: 'AFN',
        10002: 'ALL',
        10003: 'AMD',
        10004: 'ANG',
        10005: 'AOA',
        10006: 'ARS',
        10007: 'AUD',
        10008: 'AWG',
        10009: 'AZN',
        10010: 'BAM',
        10011: 'BBD',
        10012: 'BDT',
        10013: 'BGN',
        10014: 'BHD',
        10015: 'BIF',
        10016: 'BMD',
        10017: 'BND',
        10018: 'BOB',
        10019: 'BRL',
        10020: 'BSD',
        10021: 'BTN',
        10022: 'BWP',
        10023: 'BYR',
        10024: 'BZD',
        10025: 'CAD',
        10026: 'CDF',
        10027: 'CHF',
        10028: 'CLP',
        10029: 'CNY',
        10030: 'COP',
        10031: 'CRC',
        10032: 'CUP',
        10033: 'CVE',
        10034: 'CYP',
        10035: 'CZK',
        10036: 'DJF',
        10037: 'DKK',
        10038: 'DOP',
        10039: 'DZD',
        10040: 'EEK',
        10041: 'EGP',
        10042: 'ERN',
        10043: 'ETB',
        10044: 'EUR',
        10045: 'FJD',
        10046: 'FKP',
        10047: 'GBP',
        10048: 'GEL',
        10049: 'GGP',
        10050: 'GHS',
        10051: 'GIP',
        10052: 'GMD',
        10053: 'GNF',
        10054: 'GTQ',
        10055: 'GYD',
        10056: 'HKD',
        10057: 'HNL',
        10058: 'HRK',
        10059: 'HTG',
        10060: 'HUF',
        10061: 'IDR',
        10062: 'ILS',
        10063: 'IMP',
        10064: 'INR',
        10065: 'IQD',
        10066: 'IRR',
        10067: 'ISK',
        10068: 'JEP',
        10069: 'JMD',
        10070: 'JOD',
        10071: 'JPY',
        10072: 'KES',
        10073: 'KGS',
        10074: 'KHR',
        10075: 'KMF',
        10076: 'KPW',
        10077: 'KRW',
        10078: 'KWD',
        10079: 'KYD',
        10080: 'KZT',
        10081: 'LAK',
        10082: 'LBP',
        10083: 'LKR',
        10084: 'LRD',
        10085: 'LSL',
        10086: 'LTL',
        10087: 'LVL',
        10088: 'LYD',
        10089: 'MAD',
        10090: 'MDL',
        10091: 'MGA',
        10092: 'MKD',
        10093: 'MMK',
        10094: 'MNT',
        10095: 'MOP',
        10096: 'MRO',
        10097: 'MTL',
        10098: 'MUR',
        10099: 'MVR',
        10100: 'MWK',
        10101: 'MXN',
        10102: 'MYR',
        10103: 'MZN',
        10104: 'NAD',
        10105: 'NGN',
        10106: 'NIO',
        10107: 'NOK',
        10108: 'NPR',
        10109: 'NZD',
        10110: 'OMR',
        10111: 'PAB',
        10112: 'PEN',
        10113: 'PGK',
        10114: 'PHP',
        10115: 'PKR',
        10116: 'PLN',
        10117: 'PYG',
        10118: 'QAR',
        10119: 'RON',
        10120: 'RSD',
        10121: 'RUB',
        10122: 'RWF',
        10123: 'SAR',
        10124: 'SBD',
        10125: 'SCR',
        10126: 'SDG',
        10127: 'SEK',
        10128: 'SGD',
        10129: 'SHP',
        10130: 'SLL',
        10131: 'SOS',
        10132: 'SPL',
        10133: 'SRD',
        10134: 'STD',
        10135: 'SVC',
        10136: 'SYP',
        10137: 'SZL',
        10138: 'THB',
        10139: 'TJS',
        10140: 'TMM',
        10141: 'TND',
        10142: 'TOP',
        10143: 'TRY',
        10144: 'TTD',
        10145: 'TVD',
        10146: 'TWD',
        10147: 'TZS',
        10148: 'UAH',
        10149: 'UGX',
        10150: 'USD',
        10151: 'UYU',
        10152: 'UZS',
        10153: 'VEB',
        10154: 'VEF',
        10155: 'VND',
        10156: 'VUV',
        10157: 'WST',
        10158: 'XAF',
        10159: 'XAG',
        10160: 'XAU',
        10161: 'XCD',
        10162: 'XDR',
        10163: 'XOF',
        10164: 'XPD',
        10165: 'XPF',
        10166: 'XPT',
        10167: 'YER',
        10168: 'ZAR',
        10169: 'ZMK',
        10170: 'ZWD',

    }
    if key:
        return currency[key]
    if value:
        for code, name in currency.items():
            if name == value:
                return code
    return currency



def get_regions_and_states(lookup_value=None):
    regions_and_states = {
        60000: 'Alabama',
        60001: 'Alaska',
        60002: 'American Samoa',
        60003: 'AA (Armed Forces Americas)',
        60004: 'AE (Armed Forces Europe)',
        60005: 'AP (Armed Forces Pacific)',
        60006: 'Arizona',
        60007: 'Arkansas',
        60008: 'California',
        60009: 'Colorado',
        60010: 'Connecticut',
        60011: 'Delaware',
        60012: 'District of Columbia',
        60013: 'Federated States of Micronesia',
        60014: 'Florida',
        60015: 'Georgia',
        60016: 'Guam',
        60017: 'Hawaii',
        60018: 'Idaho',
        60019: 'Illinois',
        60020: 'Indiana',
        60021: 'Iowa',
        60022: 'Kansas',
        60023: 'Kentucky',
        60024: 'Louisiana',
        60025: 'Maine',
        60026: 'Marshall Islands',
        60027: 'Maryland',
        60028: 'Massachusetts',
        60029: 'Michigan',
        60030: 'Minnesota',
        60031: 'Mississippi',
        60032: 'Missouri',
        60033: 'Montana',
        60034: 'Northern Mariana Islands',
        60035: 'Nebraska',
        60036: 'Nevada',
        60037: 'New Hampshire',
        60038: 'New Jersey',
        60039: 'New Mexico',
        60040: 'New York',
        60041: 'North Carolina',
        60042: 'North Dakota',
        60043: 'Ohio',
        60044: 'Oklahoma',
        60045: 'Oregon',
        60046: 'Palau',
        60047: 'Pennsylvania',
        60048: 'Puerto Rico',
        60049: 'Rhode Island',
        60050: 'South Carolina',
        60051: 'South Dakota',
        60052: 'Tennessee',
        60053: 'Texas',
        60054: 'Utah',
        60055: 'Vermont',
        60056: 'Virgin Islands',
        60057: 'Virginia',
        60058: 'Washington',
        60059: 'West Virginia',
        60060: 'Wisconsin',
        60061: 'Wyoming',
        60062: 'Alberta',
        60063: 'British Columbia',
        60064: 'Manitoba',
        60065: 'New Brunswick',
        60066: 'Newfoundland and Labrador',
        60067: 'Northwest Territories',
        60068: 'Nova Scotia',
        60069: 'Nunavut',
        60070: 'Ontario',
        60071: 'Prince Edward Island',
        60072: 'Quebec',
        60073: 'Saskatchewan',
        60074: 'Yukon Territory',
        60075: 'Alderney',
        60076: 'County Antrim',
        60077: 'County Armagh',
        60078: 'Avon',
        60079: 'Bedfordshire',
        60080: 'Berkshire',
        60081: 'Borders',
        60082: 'Buckinghamshire',
        60083: 'Cambridgeshire',
        60084: 'Central',
        60085: 'Cheshire',
        60086: 'Cleveland',
        60087: 'Clwyd',
        60088: 'Cornwall',
        60089: 'Cumbria',
        60090: 'Derbyshire',
        60091: 'Devon',
        60092: 'Dorset',
        60093: 'County Down',
        60094: 'Dumfries and Galloway',
        60095: 'County Durham',
        60096: 'Dyfed',
        60097: 'Essex',
        60098: 'County Fermanagh',
        60099: 'Fife',
        60100: 'Mid Glamorgan',
        60101: 'South Glamorgan',
        60102: 'West Glamorgan',
        60103: 'Gloucester',
        60104: 'Grampian',
        60105: 'Guernsey',
        60106: 'Gwent',
        60107: 'Gwynedd',
        60108: 'Hampshire',
        60109: 'Hereford and Worcester',
        60110: 'Hertfordshire',
        60111: 'Highlands',
        60112: 'Humberside',
        60113: 'Isle of Man',
        60114: 'Isle of Wight',
        60115: 'Jersey',
        60116: 'Kent',
        60117: 'Lancashire',
        60118: 'Leicestershire',
        60119: 'Lincolnshire',
        60120: 'Greater London',
        60121: 'County Londonderry',
        60122: 'Lothian',
        60123: 'Greater Manchester',
        60124: 'Merseyside',
        60125: 'Norfolk',
        60126: 'Northamptonshire',
        60127: 'Northumberland',
        60128: 'Nottinghamshire',
        60129: 'Orkney',
        60130: 'Oxfordshire',
        60131: 'Powys',
        60132: 'Shropshire',
        60133: 'Sark',
        60134: 'Shetland',
        60135: 'Somerset',
        60136: 'Staffordshire',
        60137: 'Strathclyde',
        60138: 'Suffolk',
        60139: 'Surrey',
        60140: 'East Sussex',
        60141: 'West Sussex',
        60142: 'Tayside',
        60143: 'Tyne and Wear',
        60144: 'County Tyrone',
        60145: 'Warwickshire',
        60146: 'Western Isles',
        60147: 'West Midlands',
        60148: 'Wiltshire',
        60149: 'North Yorkshire',
        60150: 'South Yorkshire',
        60151: 'West Yorkshire',
        60152: 'Australian Capital Territory',
        60153: 'New South Wales',
        60154: 'Northern Territory',
        60155: 'Queensland',
        60156: 'South Australia',
        60157: 'Tasmania',
        60158: 'Victoria',
        60159: 'Western Australia',
        60160: 'Auckland',
        60161: 'Bay of Plenty',
        60162: 'Canterbury',
        60163: 'Gisborne',
        60164: "Hawke's Bay",
        60165: 'Manawatu',
        60166: 'Marlborough',
        60167: 'Nelson',
        60168: 'Northland',
        60169: 'Otago',
        60170: 'Southland',
        60171: 'Taranaki',
        60172: 'Tasman',
        60173: 'Waikato',
        60174: 'Wellington',
        60175: 'West Coast',
        60200: 'Washington DC',
    }
    if lookup_value:
        return regions_and_states[lookup_value]
    return lookup_value



def get_country(lookup_value=None):
    country = {
        8000: 'Afghanistan',
        8002: 'Aland Islands',
        8003: 'Albania',
        8004: 'Algeria',
        8005: 'American Samoa',
        8006: 'Andorra',
        8007: 'Angola',
        8008: 'Anguilla',
        8009: 'Antarctica',
        8010: 'Antigua and Barbuda',
        8011: 'Argentina',
        8012: 'Armenia',
        8013: 'Aruba',
        8014: 'Australia',
        8015: 'Austria',
        8016: 'Azerbaijan',
        8017: 'Bahamas',
        8018: 'Bahrain',
        8019: 'Bangladesh',
        8020: 'Barbados',
        8021: 'Belarus',
        8022: 'Belgium',
        8023: 'Belize',
        8024: 'Benin',
        8025: 'Bermuda',
        8026: 'Bhutan',
        8027: 'Bolivia',
        8028: 'Bosnia and Herzegovina',
        8029: 'Botswana',
        8030: 'Bouvet Island',
        8031: 'Brazil',
        8032: 'British Indian Ocean Territory',
        8033: 'British Virgin Islands',
        8034: 'Brunei',
        8035: 'Bulgaria',
        8036: 'Burkina Faso',
        8037: 'Burundi',
        8038: 'Cambodia',
        8039: 'Cameroon',
        8040: 'Canada',
        8041: 'Cape Verde',
        8042: 'Cayman Islands',
        8043: 'Central African Republic',
        8044: 'Chad',
        8045: 'Chile',
        8046: 'China',
        8047: 'Christmas Island',
        8048: 'Cocos Islands',
        8049: 'Colombia',
        8050: 'Comoros',
        8051: 'Congo - Brazzaville',
        8052: 'Congo - Kinshasa',
        8053: 'Cook Islands',
        8054: 'Costa Rica',
        8055: 'Croatia',
        8056: 'Cuba',
        8057: 'Cyprus',
        8058: 'Czech Republic',
        8059: 'Denmark',
        8060: 'Djibouti',
        8061: 'Dominica',
        8062: 'Dominican Republic',
        8063: 'East Timor',
        8064: 'Ecuador',
        8065: 'Egypt',
        8066: 'El Salvador',
        8067: 'Equatorial Guinea',
        8068: 'Eritrea',
        8069: 'Estonia',
        8070: 'Ethiopia',
        8071: 'Falkland Islands',
        8072: 'Faroe Islands',
        8073: 'Fiji',
        8074: 'Finland',
        8075: 'France',
        8076: 'French Guiana',
        8077: 'French Polynesia',
        8078: 'French Southern Territories',
        8079: 'Gabon',
        8080: 'Gambia',
        8081: 'Georgia',
        8082: 'Germany',
        8083: 'Ghana',
        8084: 'Gibraltar',
        8085: 'Greece',
        8086: 'Greenland',
        8087: 'Grenada',
        8088: 'Guadeloupe',
        8089: 'Guam',
        8090: 'Guatemala',
        8091: 'Guernsey',
        8092: 'Guinea',
        8093: 'Guinea-Bissau',
        8094: 'Guyana',
        8095: 'Haiti',
        8096: 'Heard Island and McDonald Islands',
        8097: 'Honduras',
        8098: 'Hong Kong',
        8099: 'Hungary',
        8100: 'Iceland',
        8101: 'India',
        8102: 'Indonesia',
        8103: 'Iran',
        8104: 'Iraq',
        8105: 'Ireland',
        8106: 'Isle of Man',
        8107: 'Israel',
        8108: 'Italy',
        8109: 'Ivory Coast',
        8110: 'Jamaica',
        8111: 'Japan',
        8112: 'Jersey',
        8113: 'Jordan',
        8114: 'Kazakhstan',
        8115: 'Kenya',
        8116: 'Kiribati',
        8117: 'Kuwait',
        8118: 'Kyrgyzstan',
        8119: 'Laos',
        8120: 'Latvia',
        8121: 'Lebanon',
        8122: 'Lesotho',
        8123: 'Liberia',
        8124: 'Libya',
        8125: 'Liechtenstein',
        8126: 'Lithuania',
        8127: 'Luxembourg',
        8128: 'Macao',
        8129: 'Macedonia',
        8130: 'Madagascar',
        8131: 'Malawi',
        8132: 'Malaysia',
        8133: 'Maldives',
        8134: 'Mali',
        8135: 'Malta',
        8136: 'Marshall Islands',
        8137: 'Martinique',
        8138: 'Mauritania',
        8139: 'Mauritius',
        8140: 'Mayotte',
        8141: 'Mexico',
        8142: 'Micronesia',
        8143: 'Moldova',
        8144: 'Monaco',
        8145: 'Mongolia',
        8146: 'Montenegro',
        8147: 'Montserrat',
        8148: 'Morocco',
        8149: 'Mozambique',
        8150: 'Myanmar',
        8151: 'Namibia',
        8152: 'Nauru',
        8153: 'Nepal',
        8154: 'Netherlands',
        8155: 'Netherlands Antilles',
        8156: 'New Caledonia',
        8157: 'New Zealand',
        8158: 'Nicaragua',
        8159: 'Niger',
        8160: 'Nigeria',
        8161: 'Niue',
        8162: 'Norfolk Island',
        8163: 'North Korea',
        8164: 'Northern Mariana Islands',
        8165: 'Norway',
        8166: 'Oman',
        8167: 'Pakistan',
        8168: 'Palau',
        8169: 'Palestinian Territory',
        8170: 'Panama',
        8171: 'Papua New Guinea',
        8172: 'Paraguay',
        8173: 'Peru',
        8174: 'Philippines',
        8175: 'Pitcairn',
        8176: 'Poland',
        8177: 'Portugal',
        8178: 'Puerto Rico',
        8179: 'Qatar',
        8180: 'Reunion',
        8181: 'Romania',
        8182: 'Russia',
        8183: 'Rwanda',
        8184: 'Saint Barthélemy',
        8185: 'Saint Helena',
        8186: 'Saint Kitts and Nevis',
        8187: 'Saint Lucia',
        8188: 'Saint Martin',
        8189: 'Saint Pierre and Miquelon',
        8190: 'Saint Vincent and the Grenadines',
        8191: 'Samoa',
        8192: 'San Marino',
        8193: 'Sao Tome and Principe',
        8194: 'Saudi Arabia',
        8195: 'Senegal',
        8196: 'Serbia',
        8197: 'Serbia and Montenegro',
        8198: 'Seychelles',
        8199: 'Sierra Leone',
        8200: 'Singapore',
        8201: 'Slovakia',
        8202: 'Slovenia',
        8203: 'Solomon Islands',
        8204: 'Somalia',
        8205: 'South Africa',
        8206: 'South Georgia and the South Sandwich Islands',
        8207: 'South Korea',
        8208: 'Spain',
        8209: 'Sri Lanka',
        8210: 'Sudan',
        8211: 'Suriname',
        8212: 'Svalbard and Jan Mayen',
        8213: 'Swaziland',
        8214: 'Sweden',
        8215: 'Switzerland',
        8216: 'Syria',
        8217: 'Taiwan',
        8218: 'Tajikistan',
        8219: 'Tanzania',
        8220: 'Thailand',
        8221: 'Togo',
        8222: 'Tokelau',
        8223: 'Tonga',
        8224: 'Trinidad and Tobago',
        8225: 'Tunisia',
        8226: 'Turkey',
        8227: 'Turkmenistan',
        8228: 'Turks and Caicos Islands',
        8229: 'Tuvalu',
        8230: 'U.S. Virgin Islands',
        8231: 'Uganda',
        8232: 'Ukraine',
        8233: 'United Arab Emirates',
        8234: 'United Kingdom',
        8235: 'United States',
        8236: 'United States Minor Outlying Islands',
        8237: 'Uruguay',
        8238: 'Uzbekistan',
        8239: 'Vanuatu',
        8240: 'Vatican',
        8241: 'Venezuela',
        8242: 'Vietnam',
        8243: 'Wallis and Futuna',
        8244: 'Western Sahara',
        8245: 'Yemen',
        8246: 'Zambia',
        8247: 'Zimbabwe',

    }
    if lookup_value:
        return country[lookup_value]
    return country


def get_order_origin(lookup_value=None):
    order_origin = {
        3000: 'Manual',
        3003: 'Trade Me',
        3004: 'Shopify'
    }
    if lookup_value:
        return order_origin[lookup_value]
    return order_origin

