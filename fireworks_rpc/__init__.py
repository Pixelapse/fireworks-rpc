import socket

from cStringIO import StringIO
from lxml import etree
from xml.etree.ElementTree import Element, SubElement, tostring

FIREWORKS_PORT=12124

FIREWORKS_INVALIDOBJ_ID='0'

class FireworksException(Exception):
  def __init__(self, code=1):
    self.code = code

class FireworksConn(object):
  def __init__(self, host='localhost', port=FIREWORKS_PORT):
    self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.socket.connect((host, port))
    
    # Connection specific objects
    self.fw = FireworksObj(self, 'fw')
    self.errors = FireworksObj(self, 'Errors')
    self.smartShape = FireworksObj(self, 'smartShape')
    self.invalid = FireworksObj(self, FIREWORKS_INVALIDOBJ_ID)
    
    # Deprecated
    self.document = FireworksObj(self, 'Document')
  
  def send(self, xml):
    self.socket.send(xml + '\0')
  
  def recv_null(self):
    result = StringIO()
    char = self.socket.recv(1)
    while ord(char):
      result.write(char)
      char = self.socket.recv(1)
    
    return result.getvalue()
  
  def request(self, xml):
    if isinstance(xml, Element):
      xml = tostring(xml, 'UTF-8', 'html')
  
    print xml
    self.send(xml)
    return_string = self.recv_null()
    print return_string
    return_elem = etree.fromstring(return_string)
    
    if return_elem is not None and len(return_elem) > 0:
      error_code = return_elem.get('error', None)
    
      if error_code is not None:
        raise FireworksException(error_code)
      else:
        return xml_to_value(self, return_elem[0])
    else:
      raise FireworksException()

class CallForwarder(object):
  def __init__(self, obj):
    self.obj = obj
  
  def __getattr__(self, name):
    obj = self.obj
  
    def fun(*args):
      return obj.call(name, *args)
    
    return fun
      
class FireworksObj(object):
  def __init__(self, conn, id, cls=None):
    self.conn = conn
    self.id = id
    
    self.fn = CallForwarder(self)
  
  def call(self, fun, *args):
    request = Element('func', {'obj': self.id, 'name': fun})
    
    for i, arg in enumerate(args):
      request.append(value_to_xml(arg, order=i))
    
    return self.conn.request(request)
  
  def __getitem__(self, name):
    request = Element('get', {'obj': self.id, 'name': name})
    
    try:
      return self.conn.request(request)
    except FireworksException:
      raise AttributeError()
  
  def __setitem__(self, name, value):
    if name in self.__dict__:
      self.__dict__[name] = value
    
    request = Element('set', {'obj': self.id, 'name': name, 'value': value_to_xml(value, order='0')})
    
    self.conn.request(request)
  
  def release(self):
    request = Element('release', {'obj': self.id})
    
    self.conn.request(request)

class FireworksVoid(object):
  pass

VOID = FireworksVoid()

FW_MAXINT = 2**31-1
FW_MININT = -(2**31)

def value_to_xml(value, key=None, order=None):
  """Convert a value to an XML element that we can insert"""
  
  result = None
  
  if value is None:
    # Represent None as null
    result = Element('null')
  elif isinstance(value, bool):
    result = Element('bool', {'value': 'true' if value else 'false'})
  elif isinstance(value, int):
    result = Element('int', {'value': str(value)})
  elif isinstance(value, long):
    if FW_MININT <= value and value << FW_MAXINT:
      result = Element('int', {'value': str(value)})
    else:
      raise ValueError("Long value too large for Fireworks")
  elif isinstance(value, float):
    result = Element('double', {'value': str(value)})
  elif isinstance(value, basestring):
    # Assume the library will do the escaping for us
    result = Element('string', {'value': value})
  # CHECK FOR OBJECT BEFORE ACCESSING RANDOM ATTRIBUTES
  elif isinstance(value, FireworksObj):
    # No need to specify class to send to Fireworks
    result = Element('obj', {'value': str(value.id)})
  elif isinstance(value, FireworksVoid):
    # Not sure about this...
    return Element('void')
  elif hasattr(value, 'keys'):
    # Build a dictionary tree
    result = Element('dict')
    
    if(hasattr(value, 'iteritems')):
      for (key, value) in value.iteritems():
        result.append(value_to_xml(value, key=key))
    elif hasattr(value, '__iter__'):
      for key in value:
        result.append(value_to_xml(value[key], key=key))
    else:
      for key in value.keys():
        result.append(value_to_xml(value[key], key=key))
  elif hasattr(value, '__iter__'):
    # Some kind of array, don't know what
    for item in value:
      result.append(value_to_xml(item))
  
  if result is None:
    raise ValueError("Cannot convert value to Fireworks XML Element")
  
  if key is not None:
    result.set('key', key)
  if order is not None:
    result.set('order', str(order))

  return result

def xml_to_value(conn, element):
  """Convert an element to a Python value"""
  
  if element.tag == 'null':
    return None
  elif element.tag == 'bool':
    return element.get('value') == 'true'
  elif element.tag == 'int':
    return int(element.get('value'))
  elif element.tag == 'double':
    return float(element.get('value'))
  elif element.tag == 'string':
    return element.get('value')
  elif element.tag == 'dict':
    result = {}
    
    for child in element:
      result[child.get('key')] = xml_to_value(conn, child)
  elif element.tag == 'array':
    [xml_to_value(child) for child in element]
  elif element.tag == 'obj':
    return FireworksObj(conn, element.get('value'), cls=element.get('class'))
  elif element.tag == 'void':
    return VOID
