var app = angular.module("mainApp", ['ngStorage', 'ngAnimate', 'ui.bootstrap', 'nya.bootstrap.select', 'btford.markdown', 'ui.router', 'ui.grid', 'ui.grid.resizeColumns', 'ui.grid.autoResize', 'ui.grid.moveColumns']);

app.config(function($stateProvider, $urlRouterProvider) {

  $stateProvider

  .state('content', {

      url: '/content',
      templateUrl: 'content.html',
      controller: 'VCFFilterController'

  })

  .state('content.vcfload', {

      url: '/vcfload',
      templateUrl: 'content-vcfload.html'
  })

  .state('content.wormtables', {

      url: '/wormtables',
      templateUrl: 'content-wormtables.html'
  })

  .state('content.filters', {

      url: '/filters',
      templateUrl: 'content-filters.html'
  })

  .state('content.export', {

    url: '/export',
    templateUrl: 'content-export.html'

  })

  .state('content.about', {
    url: '/about',
    templateUrl: 'content-info.html',
    '#': 'about'
  })

  .state('content.contact', {
    url: '/contact',
    templateUrl: 'content-info.html',
    '#': 'contact'
  })

  .state('content.faq', {
    url: '/faq',
    templateUrl: 'content-info.html',
    '#': 'faq'
  })

  $urlRouterProvider.otherwise('/content/vcfload');


});

//make history prettier by removing underscores and 'opt' prefixes
app.filter('prettifyHistory', function() {

  return function(text) {

    return String(text).replace(/_/g, ' ').replace(/opt [a-zA-z]/g, '');
  }

});

//don't show the first element of the history list, which is the total count
app.filter('startFrom', function() {
  return function(arr, start) {
    return arr.slice(start);
  };
});

app.controller('VCFFilterController', function($scope, $sce, $state, $sessionStorage, $http, $window) {

    $scope.$storage = $sessionStorage;

    $scope.isLoadingVCF = undefined;
    $scope.isIndexingVCF = undefined;
    $scope.isFilteringVCF = undefined;
    $scope.isRemovingHistoryItem = false;

    //form data for http POSTs
    $scope.formData = {};

    //load option values for filtering

    //this gets populated based on the fields chosen for wormtable parsing in step 2
    //for script 03
    $scope.opt_a_field_to_filter_variants = ['Option A', 'Option B', 'Option C'];

    //these are static values for script 03
    $scope.opt_a_operator = ['greater_than', 'less_than', 'equal_to', 'contains_keyword'];

    //filter B is enabled unless we don't have sample genotypes in the VCF
    $scope.nofilterb = false;

    //'het' or 'hom' gets passed as script 04's -g argument.
    $scope.opt_b_genotype = {'het': 'Heterozygous', 'homref':'Homozygous Ref', 'homalt':'Homozygous Alt'};

    //this should populate from the preprocessed VCF file
    $scope.opt_b_sample = ['First Option', 'Second Option'];

    $scope.opt_d_variant_type = ['SNPs', 'InDels', 'MNPs'];

    $scope.opt_e_keyword_field = ['First Option', 'Second Option'];
    $scope.opt_e_genelist = ['G1', 'G2'];

    //map field variable names to human-readable ones
    $scope.field_name_map = {
        'opt_a_operator': 'Operator',
        'opt_a_cutoff': 'Cutoff',
        'opt_a_field_to_filter_variants': 'Chosen field for filtering',
        'opt_a_keep_none_variants': 'Keep variants having no value in the selected field',

        'opt_b_genotype': 'Genotype',
        'opt_b_sample[]': 'Samples',

        'opt_c_chromosome': 'Chromosome',
        'opt_c_start_pos': 'Start position',
        'opt_c_end_pos': 'End position',

        'opt_d_variant_type': 'Variant type',

        'opt_e_keyword_field': 'Field Name',
        'opt_e_genelist': 'List of input genes',
        'opt_e_negative_query': 'Genes excluded instead of included',

        'numresults': 'Number of variants found',
        'filterused': 'Filter Name',
        'startvar': 'Total number of starting variants'

    };

    $scope.myfields = [];

    //results of parsing...used to populate the results table
    $scope.parseresults = {};
    $scope.numresults = undefined;

    $scope.filterHistory = [];
    $scope.actionCounter = 0;

    $scope.totalvariants = 0;

    //seed a value
    $scope.vcffiles = [{"name": "/path/to/myvcf.vcf.gz"}];

    //load vcf filenames from JSON
    $http.get('js/vcfHistory.json').then(function(res) {

        $scope.vcffiles = res.data;
        $scope.formData.processVCF = $scope.vcffiles[$scope.vcffiles.length - 1].name; //name added to dropdown

    });

    $scope.availCores = '1';

    $scope.setFilter = function(filtername) {

        $scope.formData.whichFilter = filtername;

    };

    /* Save the history array to a text file */
    $scope.saveHistory = function() {

        //var histBlob = new Blob([JSON.stringify($scope.filterHistory, null, 2).replace(/[{}\[\]]/g, "")], {type: "text/plain; charset=utf-8"});
        var outputHistory = [];

        for (var i = 0; i < $scope.filterHistory.length; i++)
        {
          for (var k in $scope.filterHistory[i])
          {
             if (k != "actionNumber" && k != "$$hashKey")
             {
               if (k == "outfile")
               {
                 //extra new line ahead of next series of outputs, don't print outfile
                 outputHistory.push("\n-------\n\nFilter " + i + ":\n");
               }
               else if (k == "inputdata") //cascade into this sub-map
               {
                  outputHistory.push("\nInput Data:\n");

                  for (var kk in $scope.filterHistory[i][k])
                  {
                      if (kk == "opt_b_genotype")
                      {
                         outputHistory.push($scope.field_name_map[kk] + " --> " + $scope.opt_b_genotype[$scope.filterHistory[i][k][kk]]);
                      }
                      else
                      {
                         outputHistory.push($scope.field_name_map[kk] + " --> " + $scope.filterHistory[i][k][kk]);
                      }
                      outputHistory.push("\n");
                  }

               }
               else
               {
                 outputHistory.push($scope.field_name_map[k] + " --> " + $scope.filterHistory[i][k]);
               }

               outputHistory.push("\n");  //new line
             }
          }
        }

        var histBlob = new Blob(outputHistory, {type: "text/plain; charset=utf-8"});

        saveAs(histBlob, "ogc_vcf_history.txt");

    }



    //delete working directory and previous file history local values
    //this will trigger on load
    delete $scope.$storage.OGCWOrkingDir;
    delete $scope.$storage.OGCDownloadPath;
    delete $scope.$storage.PrevFile;

    $scope.submitUploadForm = function() {

	    $scope.isLoadingVCF = true;

      //escape backslashes for Windows paths
      $scope.formData.processVCF = $scope.formData.processVCF.replace(/\\/g,"\\\\");

	    var request = $http({

	        method: "post",
	        url: "cgi-bin/vcfload.py",
	        data: $.param($scope.formData),
	        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }

	    });

	    request.success(function(success) {

          $scope.sendSucceed = true;
          $scope.isLoadingVCF = false;

          if (success.ERRMSG != "None")
          {
            //throw an alert
            alert("The VCF file could not be processed.\nThis is usually because the input VCF contains a duplicate line or some other formatting quirk.\nPlease try another file.\nFor reference, the error I got was:\n" + success.ERRMSG);
          }

          else
          {
            $scope.myfields = success.filterfields;

            if (success.nofilterb === true)
            {
              $scope.nofilterb = true;
            }

            //set working directory variables
            $scope.$storage.OGCWOrkingDir = success.workingdir;
            $scope.$storage.OGCDownloadPath = success.downloadpath;

            //clear the history and previous results
            delete $scope.$storage.PrevFile;
            $scope.filterHistory = [];
            $scope.numresults = undefined;
            $scope.parseresults.data = [];

            //move the wizard along to the next state
            $state.go('content.wormtables');

            $scope.availCores = success.numCores;

          }
	    });


    }

    $scope.submitFieldIndexForm = function() {

	    $scope.isIndexingVCF = true;

      //add the working directory
      $scope.formData.OGCWOrkingDir = $scope.$storage.OGCWOrkingDir;

	    var request = $http({

	        method: "post",
	        url: "cgi-bin/createindexes.py",
	        data: $.param($scope.formData),
	        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }

	    });

	    request.success(function(success) {
        
        $scope.sendSucceed = true;
        $scope.isIndexingVCF = false;

        if (success.ERRMSG != "None")
        {
          //throw an alert
          alert("The VCF file could not be processed.\nThis is usually because the input VCF contains a duplicate line or some other formatting quirk.\nPlease try another file.\nFor reference, the error I got was:\n" + success.ERRMSG);
        }

        else
        {
          $scope.opt_a_field_to_filter_variants = success.indexedfields;
          $scope.opt_e_keyword_field = success.indexedfields;

          $scope.opt_b_sample = success.availsamples_filterb;

          if (success.nofilterb == true)
          {
            $scope.nofilterb = true;
          }
          else {
            $scope.nofilterb = false;
          }

          $scope.totalvariants = success.totalvariants;

          if ($scope.filterHistory.length < 1)
          {
            $scope.filterHistory.push({'startvar': success.totalvariants, 'actionNumber': -1});
          }

          //move the wizard along to the next state
          $state.go('content.filters');

        }

	    });

    }



    //what happens when the filtering form is clicked?
    //it sends all the radio button/checkbox/text box data to cgi-bin/filter.py
    //where it will be digested in Python to invoke Silvia's scripts
    $scope.submitFilterForm = function() {

        $scope.isFilteringVCF = true;

        //add the working directory
        $scope.formData.OGCWOrkingDir = $scope.$storage.OGCWOrkingDir;
        $scope.formData.PrevFile = $scope.$storage.PrevFile;

        var request = $http({

            method: "post",
            url: "cgi-bin/filter.py",
            data: $.param($scope.formData),
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' }

        });

        request.success(function(success) {

            $scope.sendSucceed = true;
            $scope.isFilteringVCF = false;

            //load the json results into the scope if we had results
            //otherwise, let the user know
            if (success.numresults > 0)
            {

              //increment the action counter
              $scope.actionCounter = $scope.actionCounter + 1;

              //set previous file cookie
              $scope.$storage.PrevFile = success.prevfile;

              $scope.parseresults.columnDefs = success.outheadermap;
              $scope.parseresults.data = angular.fromJson(success.outtextmap);
              $scope.numresults = success.numresults;

              //add it to the history
              $scope.filterHistory.push({

                  'outfile': success.outfile,
                  'numresults': success.numresults,
                  'inputdata': success.inputdata,
                  'filterused': success.filtervals,
                  'actionNumber': $scope.actionCounter  //which action are we on? this will determine where the 'delete' icon goes

              });
            }

            else {
              alert("This filter did not produce any results, please try again.\n" + success.numresults)
            }

        })

    }

    //when we roll back the history to the previous state...
    $scope.removeHistoryItem = function(currentfilename) {

        //console.log(currentfilename);

        //change the trash icon to a non-clickable spinner
        $scope.isRemovingHistoryItem = true;

        var request = $http({

          method: "post",
          url: "cgi-bin/rollback.py",
          data: $.param({'workingdir': $scope.$storage.OGCWOrkingDir, 'remFilename': currentfilename}),
          headers: { 'Content-Type': 'application/x-www-form-urlencoded'}

        });

        //remove the filter from the history
        request.success(function(success) {

            //get rid of the spinner button that's tied to this being true
            $scope.isRemovingHistoryItem = false;

            //rollback the sessionStorage and counter for displaying the next delete button
            $scope.$storage.PrevFile = success.newPrevFile;
            $scope.actionCounter = $scope.actionCounter - 1;

            //reload the new (old) grid results if there are any
            if (success.numresults >= 0) {
              $scope.parseresults.columnDefs = success.outheadermap;
              $scope.parseresults.data = angular.fromJson(success.outtextmap);
              $scope.numresults = success.numresults;
            }

            //finally, pop the history item off the list
            $scope.filterHistory.pop();

            if (success.rewindedToBeginning === true)
            {
              delete $scope.$storage.PrevFile; //so we don't pass a -p parameter to Silvia's scripts
            }

        });



    };



});
