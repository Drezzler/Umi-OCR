

class KeyList:
    '''
Data structure used to maintain a table list of images.
    It can be accessed through the key key and the subscript index.
    Each item of data is a dictionary.
    '''

    def __init__(self):
        self.__dataList = []
        self.__dataDict = {}

    # =============== 增 ==============================
    def append(self, key, data):
        '''Insert an element at the end, specify the key and content'''
        self.__dataDict[key] = data
        self.__dataList.append(key)

    # =============== 删 ==============================
    def delete(self, key=None, index=-1):
        '''Delete the specified element. Pass in key or index. '''
        if self.isKey(key):
            del self.__dataDict[key]
            self.__dataList.remove(key)
        elif self.isIndex(index):
            k = self.indexToKey(index)
            del self.__dataDict[k]
            del self.__dataList[index]
        else:
            raise Exception(
                f'List delete : 请传入合法的key或index！当前为 {key} , {index}')

    def clear(self):
        '''清空全部元素'''
        self.__dataList.clear()
        self.__dataDict.clear()

    # =============== 查 ==============================
    def len(self):
        '''返回长度'''
        return len(self.__dataList)

    def isEmpty(self):
        '''空返回True'''
        return len(self.__dataList) <= 0

    def isKey(self, key):
        '''若存在键为key的项，返回True'''
        return key in self.__dataDict

    def isIndex(self, index):
        '''若index合法，返回True'''
        return index >= 0 and index < len(self.__dataList)

    def indexToKey(self, index):
        '''传入index，返回该项的key'''
        return self.__dataList[index]

    def get(self, key=None, index=-1):
        '''Query the specified element. Pass in key or index and return data. '''
        if self.isKey(key):
            return self.__dataDict[key]
        elif self.isIndex(index):
            return self.__dataDict[self.__dataList[index]]
        else:
            raise Exception(f'List get: Please pass in a legal key or index! Currently it is {key}, {index}')

    def getKeys(self):
        '''return key list'''
        return self.__dataDict.keys()

    def getItemValueList(self, dKey):
        '''Extract the values corresponding to dKey in all data into a list'''
        return [d[dKey] for d in self.__dataDict.values()]

    def isDataItem(self, dKey, dValue):
        '''Check whether there is an element with key dKey and value dValue in all data, and return True'''
        for d in self.__dataDict.values():
            if dKey in d and d[dKey] == dValue:
                return True
        return False
