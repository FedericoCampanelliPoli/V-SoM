function moveGeneratedFiles()
    % Define the source and destination
    sourceFiles = dir('**/ISR.c'); % Get all .c files in current and subdirectories
    destinationFolder = '..\..\H755_Code\V-SoM\CM4\Core\Src';

    sourceFilePath = fullfile(sourceFiles.folder, sourceFiles.name);
    copyfile(sourceFilePath, destinationFolder);

        % Define the source and destination
    sourceFiles = dir('**/ISR.h'); % Get all .c files in current and subdirectories
    destinationFolder = '..\..\H755_Code\V-SoM\CM4\Core\Inc';

    sourceFilePath = fullfile(sourceFiles.folder, sourceFiles.name);
    copyfile(sourceFilePath, destinationFolder);

end
