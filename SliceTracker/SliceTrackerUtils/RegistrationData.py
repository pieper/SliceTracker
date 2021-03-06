import logging
import slicer
import os, json
from collections import OrderedDict

from SlicerProstateUtils.constants import FileExtension
from SlicerProstateUtils.mixins import ModuleLogicMixin
from SlicerProstateUtils.decorators import onExceptionReturnNone
from SlicerProstateUtils.mixins import ModuleWidgetMixin


class RegistrationResults(ModuleWidgetMixin):

  @property
  def activeResult(self):
    return self._getActiveResult()

  @activeResult.setter
  def activeResult(self, series):
    assert series in self._registrationResults.keys()
    self._activeResult = series

  @property
  @onExceptionReturnNone
  def originalTargets(self):
    return self.getMostRecentApprovedCoverProstateRegistration().originalTargets

  @property
  @onExceptionReturnNone
  def intraopLabel(self):
    return self.getMostRecentApprovedCoverProstateRegistration().fixedLabel

  def __init__(self):
    self.resetAndInitializeData()

  def resetAndInitializeData(self):
    self._activeResult = None
    self.preopTargets = None
    self._savedRegistrationResults = []
    self._registrationResults = OrderedDict()
    self.customProgressBar = self.getOrCreateCustomProgressBar()

  def loadFromJSON(self, directory, filename):
    self.resetAndInitializeData()
    self.alreadyLoadedFileNames = {}
    with open(filename) as data_file:
      data = json.load(data_file)
      for index, (name, jsonResult) in enumerate(data["results"].iteritems()):
        result = self.createResult(name)
        self.customProgressBar.visible = True
        self.customProgressBar.maximum = len(data["results"])
        self.customProgressBar.updateStatus("Loading series registration result %s" % result.name, index+1)
        slicer.app.processEvents()
        for attribute, value in jsonResult.iteritems():
          if attribute == 'volumes':
            self._loadResultFileData(value, directory, slicer.util.loadVolume, result.setVolume)
          elif attribute == 'transforms':
            self._loadResultFileData(value, directory, slicer.util.loadTransform, result.setTransform)
          elif attribute == 'targets':
            self._loadResultFileData(value, directory, slicer.util.loadMarkupsFiducialList, result.setTargets)
          elif attribute in ['fixedLabel', 'movingLabel']:
            label = self._loadOrGetFileData(directory, value, slicer.util.loadLabelVolume)
            setattr(result, attribute, label)
          elif attribute in ['fixedVolume', 'movingVolume']:
            volume = self._loadOrGetFileData(directory, value, slicer.util.loadVolume)
            setattr(result, attribute, volume)
          elif attribute == 'originalTargets':
            targets = self._loadOrGetFileData(directory, value, slicer.util.loadMarkupsFiducialList)
            setattr(result, attribute, targets)
          elif attribute == 'approvedTargets':
            targets = self._loadOrGetFileData(directory, value["fileName"], slicer.util.loadMarkupsFiducialList)
            setattr(result, attribute, targets)
            approvedRegType = value["derivedFrom"]
            result.modifiedTargets[approvedRegType] = value["userModified"]
          else:
            setattr(result, attribute, value)
        if result not in self._savedRegistrationResults:
          self._savedRegistrationResults.append(result)
      self.customProgressBar.text = "Finished loading registration results"
    self._registrationResults = OrderedDict(sorted(self._registrationResults.items()))

  def _loadResultFileData(self, dictionary, directory, loadFunction, setFunction):
    for regType, filename in dictionary.iteritems():
      data = self._loadOrGetFileData(directory, filename, loadFunction)
      setFunction(regType, data)

  def _loadOrGetFileData(self, directory, filename, loadFunction):
    if not filename:
      return None
    try:
      data = self.alreadyLoadedFileNames[filename]
    except KeyError:
      _, data = loadFunction(os.path.join(directory, filename), returnNode=True)
      self.alreadyLoadedFileNames[filename] = data
    return data

  def save(self, outputDir):
    savedSuccessfully = []
    failedToSave = []
    self.customProgressBar.visible = True
    for index, result in enumerate(self._registrationResults.values()):
      self.customProgressBar.maximum = len(self._registrationResults)
      self.customProgressBar.updateStatus("Saving registration result for series %s" % result.name, index + 1)
      slicer.app.processEvents()
      if result not in self._savedRegistrationResults:
        successfulList, failedList = result.save(outputDir)
        savedSuccessfully += successfulList
        failedToSave += failedList
        self._savedRegistrationResults.append(result)
    self.customProgressBar.text = "Registration data successfully saved" if len(failedToSave) == 0 else "Error/s occurred during saving"
    return savedSuccessfully, failedToSave

  def _registrationResultHasStatus(self, series, status):
    if not type(series) is int:
      series = RegistrationResult.getSeriesNumberFromString(series)
    results = self.getResultsBySeriesNumber(series)
    return any(result.status == status for result in results) if len(results) else False

  def registrationResultWasApproved(self, series):
    return self._registrationResultHasStatus(series, RegistrationResult.APPROVED_STATUS)

  def registrationResultWasSkipped(self, series):
    return self._registrationResultHasStatus(series, RegistrationResult.SKIPPED_STATUS)

  def registrationResultWasRejected(self, series):
    return self._registrationResultHasStatus(series, RegistrationResult.REJECTED_STATUS)

  def registrationResultWasApprovedOrRejected(self, series):
    return self._registrationResultHasStatus(series, RegistrationResult.REJECTED_STATUS) or \
           self._registrationResultHasStatus(series, RegistrationResult.APPROVED_STATUS)

  def getResultsAsList(self):
    return self._registrationResults.values()

  def getMostRecentApprovedCoverProstateRegistration(self):
    mostRecent = None
    for result in self._registrationResults.values():
      if self.getSetting("COVER_PROSTATE", "SliceTracker") in result.name and result.approved:
        mostRecent = result
        break
    return mostRecent

  def getLastApprovedRigidTransformation(self):
    if sum([1 for result in self._registrationResults.values() if result.approved]) == 1:
      lastRigidTfm = None
    else:
      lastRigidTfm = self.getMostRecentApprovedResult().rigidTransform
    if not lastRigidTfm:
      lastRigidTfm = slicer.vtkMRMLLinearTransformNode()
      slicer.mrmlScene.AddNode(lastRigidTfm)
    return lastRigidTfm

  @onExceptionReturnNone
  def getMostRecentApprovedTransform(self):
    results = sorted(self._registrationResults.values(), key=lambda s: s.seriesNumber)
    for result in reversed(results):
      if result.approved and self.getSetting("COVER_PROSTATE", "SliceTracker") not in result.name:
        return result.transforms[result.approvedRegistrationType]
    return None

  def getOrCreateResult(self, series):
    result = self.getResult(series)
    return result if result is not None else self.createResult(series)

  def createResult(self, series):
    assert series not in self._registrationResults.keys()
    self._registrationResults[series] = RegistrationResult(series)
    self.activeResult = series
    return self._registrationResults[series]

  @onExceptionReturnNone
  def getResult(self, series):
    return self._registrationResults[series]

  def getResultsBySeries(self, series):
    seriesNumber = RegistrationResult.getSeriesNumberFromString(series)
    return self.getResultsBySeriesNumber(seriesNumber)

  def getResultsBySeriesNumber(self, seriesNumber):
    return [result for result in self.getResultsAsList() if seriesNumber == result.seriesNumber]

  def removeResult(self, series):
    try:
      del self._registrationResults[series]
    except KeyError:
      pass

  def exists(self, series):
    return series in self._registrationResults.keys()

  @onExceptionReturnNone
  def _getActiveResult(self):
    return self._registrationResults[self._activeResult]

  @onExceptionReturnNone
  def getMostRecentResult(self):
    lastKey = self._registrationResults.keys()[-1]
    return self._registrationResults[lastKey]

  @onExceptionReturnNone
  def getMostRecentApprovedResult(self):
    results = sorted(self._registrationResults.values(), key=lambda s: s.seriesNumber)
    for result in reversed(results):
      if result.approved:
        return result
    return None

  @onExceptionReturnNone
  def getMostRecentApprovedResultPriorTo(self, seriesNumber):
    results = sorted(self._registrationResults.values(), key=lambda s: s.seriesNumber)
    results = [result for result in results if result.seriesNumber < seriesNumber]
    for result in reversed(results):
      if result.approved:
        return result
    return None

  @onExceptionReturnNone
  def getMostRecentVolumes(self):
    return self.getMostRecentResult().volumes

  @onExceptionReturnNone
  def getMostRecentTransforms(self):
    return self.getMostRecentResult().transforms

  @onExceptionReturnNone
  def getMostRecentTargets(self):
    return self.getMostRecentResult().targets

  @onExceptionReturnNone
  def getMostRecentApprovedTargets(self):
    return self.getMostRecentApprovedResult().approvedTargets

  @onExceptionReturnNone
  def getMostRecentApprovedTargetsPriorTo(self, seriesNumber):
    return self.getMostRecentApprovedResultPriorTo(seriesNumber).approvedTargets


class RegistrationResult(ModuleLogicMixin):

  REGISTRATION_TYPE_NAMES = ['rigid', 'affine', 'bSpline']

  SKIPPED_STATUS = 'skipped'
  APPROVED_STATUS = 'approved'
  REJECTED_STATUS = 'rejected'
  POSSIBLE_STATES = [SKIPPED_STATUS, APPROVED_STATUS, REJECTED_STATUS]

  @staticmethod
  def getSeriesNumberFromString(text):
    return int(text.split(": ")[0])

  @property
  def volumes(self):
    return {'rigid': self.rigidVolume, 'affine': self.affineVolume, 'bSpline': self.bSplineVolume}

  @property
  def transforms(self):
    return {'rigid': self.rigidTransform, 'affine': self.affineTransform, 'bSpline': self.bSplineTransform}

  @property
  def targets(self):
    return {'rigid': self.rigidTargets, 'affine': self.affineTargets, 'bSpline': self.bSplineTargets}

  @property
  @onExceptionReturnNone
  def approvedVolume(self):
    return self.volumes[self.approvedRegistrationType]

  @property
  def approved(self):
    return self.status == self.APPROVED_STATUS

  @property
  def skipped(self):
    return self.status == self.SKIPPED_STATUS

  @property
  def rejected(self):
    return self.status == self.REJECTED_STATUS

  @property
  def name(self):
    return self._name

  @name.setter
  def name(self, name):
    splitted = name.split(': ')
    assert len(splitted) == 2
    self._name = name
    self._seriesNumber = int(splitted[0])
    self._seriesDescription = splitted[1]

  @property
  def seriesNumber(self):
    return self._seriesNumber

  @property
  def seriesDescription(self):
    return self._seriesDescription

  @property
  def targetsWereModified(self):
    return len(self.modifiedTargets) > 0

  def __init__(self, series):
    self.name = series

    self.status = None

    self._initVolumes()
    self._initTransforms()
    self._initTargets()
    self._initLabels()

    self.cmdArguments = ""
    self.suffix = ""
    self.score = None

    self.modifiedTargets = {}

    self.approvedRegistrationType = None
    self.approvedTargets = None

  def getRegistrationTypeForTargetList(self, targetList):
    for regType, currentTargetList in self.targets.iteritems():
      if targetList is currentTargetList:
        return regType
    return None

  def isGoingToBeMoved(self, targetList, index):
    assert targetList in self.targets.values()
    regType = self.getRegistrationTypeForTargetList(targetList)
    if not self.modifiedTargets.has_key(regType):
      self.modifiedTargets[regType] = [False for i in range(targetList.GetNumberOfFiducials())]
    self.modifiedTargets[regType][index] = True

  def _initLabels(self):
    self.movingLabel = None
    self.fixedLabel = None

  def _initTargets(self):
    self.rigidTargets = None
    self.affineTargets = None
    self.bSplineTargets = None
    self.originalTargets = None

  def _initTransforms(self):
    self.rigidTransform = None
    self.affineTransform = None
    self.bSplineTransform = None

  def _initVolumes(self):
    self.fixedVolume = None
    self.movingVolume = None
    self.rigidVolume = None
    self.affineVolume = None
    self.bSplineVolume = None

  def _getAllFileNames(self, keyFunction):
    fileNames = {}
    for regType in self.REGISTRATION_TYPE_NAMES:
      fileNames[regType] = keyFunction(regType)
    return fileNames

  def _getFileName(self, node, extension):
    if node:
      return ModuleLogicMixin.replaceUnwantedCharacters(node.GetName()) + extension
    return None

  def setVolume(self, regType, volume):
    self._setRegAttribute(regType, "Volume", volume)

  def getVolume(self, regType):
    return self._getRegAttribute(regType, "Volume")

  def setTransform(self, regType, transform):
    self._setRegAttribute(regType, "Transform", transform)

  def getTransform(self, regType):
    return self._getRegAttribute(regType, "Transform")

  def setTargets(self, regType, targets):
    self._setRegAttribute(regType, "Targets", targets)

  def getTargets(self, regType):
    return self._getRegAttribute(regType, "Targets")

  def _setRegAttribute(self, regType, attributeType, value):
    assert regType in self.REGISTRATION_TYPE_NAMES
    setattr(self, regType+attributeType, value)

  def _getRegAttribute(self, regType, attributeType):
    assert regType in self.REGISTRATION_TYPE_NAMES
    return getattr(self, regType+attributeType)

  def approve(self, registrationType):
    assert registrationType in self.REGISTRATION_TYPE_NAMES
    self.approvedRegistrationType = registrationType
    self.status = self.APPROVED_STATUS
    self.approvedTargets = self.cloneFiducials(self.targets[self.approvedRegistrationType],
                                               cloneName="%s-TARGETS-approved" % str(self.seriesNumber), keepDisplayNode=True)

  def skip(self):
    self.status = self.SKIPPED_STATUS

  def reject(self):
    self.status = self.REJECTED_STATUS

  def printSummary(self):
    logging.debug('# ___________________________  registration output  ________________________________')
    logging.debug(self.__dict__)
    logging.debug('# __________________________________________________________________________________')

  def getApprovedTargetsModifiedStatus(self):
    try:
      modified = self.modifiedTargets[self.approvedRegistrationType]
    except KeyError:
      modified = [False for i in range(self.approvedTargets.GetNumberOfFiducials())]
    return modified

  def save(self, outputDir):
    if not os.path.exists(outputDir):
      self.createDirectory(outputDir)

    savedSuccessfully = []
    failedToSave = []

    def saveCMDParameters():
      if self.cmdArguments != "":
        filename = os.path.join(outputDir, self.cmdFileName)
        f = open(filename, 'w+')
        f.write(self.cmdArguments)
        f.close()

    def saveTransformations():
      for transformNode in [node for node in self.transforms.values() if node]:
        success, name = self.saveNodeData(transformNode, outputDir, FileExtension.H5)
        self.handleSaveNodeDataReturn(success, name, savedSuccessfully, failedToSave)

    def saveTargets():
      for targetNode in [node for node in self.targets.values()+[self.originalTargets] if node]:
        success, name = self.saveNodeData(targetNode, outputDir, FileExtension.FCSV)
        self.handleSaveNodeDataReturn(success, name, savedSuccessfully, failedToSave)

    def saveApprovedTargets():
      if self.approvedTargets:
        success, name = self.saveNodeData(self.approvedTargets, outputDir, FileExtension.FCSV)
        self.handleSaveNodeDataReturn(success, name, savedSuccessfully, failedToSave)

    def saveVolumes():
      for volumeNode in [node for node in self.volumes.values()+[self.fixedVolume, self.movingVolume] if node]:
        success, name = self.saveNodeData(volumeNode, outputDir, FileExtension.NRRD)
        self.handleSaveNodeDataReturn(success, name, savedSuccessfully, failedToSave)

    def saveLabels():
      for labelVolume in [self.fixedLabel, self.movingLabel]:
        if labelVolume:
          success, name = self.saveNodeData(labelVolume, outputDir, FileExtension.NRRD)
          self.handleSaveNodeDataReturn(success, name, savedSuccessfully, failedToSave)

    saveCMDParameters()
    saveTransformations()
    saveTargets()
    saveApprovedTargets()
    saveVolumes()
    saveLabels()
    return savedSuccessfully, failedToSave

  @property
  def cmdFileName(self):
    return str(self.seriesNumber) + "-CMD-PARAMETERS" + self.suffix + FileExtension.TXT

  def getTransformFileName(self, regType):
    return self._getFileName(self.getTransform(regType), FileExtension.H5)

  def getVolumeFileName(self, regType):
    return self._getFileName(self.getVolume(regType), FileExtension.NRRD)

  def getTargetFileName(self, regType):
    return self._getFileName(self.getTargets(regType), FileExtension.FCSV)

  def getAllTargetFileNames(self):
    return self._getAllFileNames(self.getTargetFileName)

  def getAllTransformationFileNames(self):
    return self._getAllFileNames(self.getTransformFileName)

  def getAllVolumeFileNames(self):
    return self._getAllFileNames(self.getVolumeFileName)

  def getFixedVolumeFileName(self):
    return self._getFileName(self.fixedVolume, FileExtension.NRRD)

  def getMovingVolumeFileName(self):
    return self._getFileName(self.movingVolume, FileExtension.NRRD)

  def getFixedLabelFileName(self):
    return self._getFileName(self.fixedLabel, FileExtension.NRRD)

  def getMovingLabelFileName(self):
    return self._getFileName(self.movingLabel, FileExtension.NRRD)

  def getOriginalTargetsFileName(self):
    return self._getFileName(self.originalTargets, FileExtension.FCSV)

  def getApprovedTargetsFileName(self):
    return self._getFileName(self.approvedTargets, FileExtension.FCSV)

  def toDict(self):
    dictionary = {self.name:{"targets":self.getAllTargetFileNames(), "transforms":self.getAllTransformationFileNames(),
                       "volumes":self.getAllVolumeFileNames(), "approvedRegistrationType":self.approvedRegistrationType,
                       "suffix":self.suffix, "status":self.status, "score": self.score,
                       "fixedLabel":self.getFixedLabelFileName(), "movingLabel":self.getMovingLabelFileName(),
                       "fixedVolume": self.getFixedVolumeFileName(), "movingVolume": self.getMovingVolumeFileName(),
                       "originalTargets":self.getOriginalTargetsFileName()}}
    if self.approved:
      dictionary[self.name]["approvedTargets"] = {"derivedFrom":self.approvedRegistrationType,
                                       "userModified": self.getApprovedTargetsModifiedStatus(),
                                       "fileName": self.getApprovedTargetsFileName()}
    return dictionary

