Manual step required (one-time): download the MongoDB Community Server
Windows ZIP package from https://www.mongodb.com/try/download/community
and copy bin\mongod.exe from the extracted ZIP into this folder, so the
final path is: desktop/resources/mongodb/mongod.exe

See ../../BUILD_WINDOWS.md for full details. build.bat will refuse to
package the installer until mongod.exe is present here.
